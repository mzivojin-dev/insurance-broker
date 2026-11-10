# prod environment. Filled in during episode 3 from the modules in infra/modules.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # The bucket (TF_STATE_BUCKET from infra/bootstrap) contains the account ID, so it stays out of git:
  #   terraform init -backend-config="bucket=ai4all-tf-state-$(aws sts get-caller-identity --query Account --output text)"
  backend "s3" {
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { project = "ai4all", env = "prod" }
  }
}

variable "image_tag" {
  type        = string
  description = "Git SHA of the images to run; set by deploy.yml"
  default     = "latest"
}

variable "ephemeral" {
  type        = bool
  description = <<-EOT
    true: prod is torn down every day (scripts/prod_down.sh), so RDS has no deletion
    protection or final snapshot and S3/ECR are emptied on destroy. Set false if prod
    ever runs full time with real data.
  EOT
  default     = true
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate for HTTPS on the load balancer; empty serves plain HTTP on the ALB DNS name"
  default     = ""
}

locals {
  agents = ["client_service", "submission_intake", "book_analyst"]
  https  = var.certificate_arn != ""
}

data "aws_caller_identity" "me" {}

module "vpc" {
  source = "../../modules/vpc"
  env    = "prod"
  region = "us-east-1"
}

resource "aws_ecs_cluster" "this" { name = "ai4all-prod" }

# The value is not in Terraform (it would land in the state): deploy.yml writes it from the
# ANTHROPIC_API_KEY repository secret right after creating the secret.
resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "ai4all-prod/anthropic-api-key"
  recovery_window_in_days = var.ephemeral ? 0 : 30 # 0: the name is free again for tomorrow's apply
}

resource "aws_security_group" "alb" {
  name   = "ai4all-prod-alb"
  vpc_id = module.vpc.vpc_id
  ingress {
    from_port   = local.https ? 443 : 80
    to_port     = local.https ? 443 : 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "this" {
  name            = "ai4all-prod"
  subnets         = module.vpc.public_subnet_ids
  security_groups = [aws_security_group.alb.id]
  idle_timeout    = 300 # agent runs can be slow; matches the local gateway
}

# Each agent adds a /<agent>/* rule; anything else is a 404.
resource "aws_lb_listener" "this" {
  load_balancer_arn = aws_lb.this.arn
  port              = local.https ? 443 : 80
  protocol          = local.https ? "HTTPS" : "HTTP"
  ssl_policy        = local.https ? "ELBSecurityPolicy-TLS13-1-2-2021-06" : null
  certificate_arn   = local.https ? var.certificate_arn : null
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      status_code  = "404"
    }
  }
}

output "base_url" {
  description = "scripts/smoke_check.sh target; deploy.yml smoke-checks it after apply"
  value       = "${local.https ? "https" : "http"}://${aws_lb.this.dns_name}"
}
resource "aws_s3_bucket" "docs" {
  bucket        = "ai4all-prod-docs-${data.aws_caller_identity.me.account_id}"
  force_destroy = var.ephemeral
}

# Every agent task wears this group and the database trusts it. Trusting each service's own
# group instead would be a cycle: the services need the database address first.
resource "aws_security_group" "app" {
  name        = "ai4all-prod-app"
  description = "ECS tasks allowed to reach the database"
  vpc_id      = module.vpc.vpc_id
}

module "db" {
  source                     = "../../modules/rds_pgvector"
  env                        = "prod"
  ephemeral                  = var.ephemeral
  vpc_id                     = module.vpc.vpc_id
  db_subnet_group            = module.vpc.db_subnet_group
  allowed_security_group_ids = [aws_security_group.app.id]
}

module "services" {
  source       = "../../modules/ecs_service"
  for_each     = toset(local.agents)
  name         = each.key
  env          = "prod"
  ephemeral    = var.ephemeral
  image_tag    = var.image_tag
  cluster_arn  = aws_ecs_cluster.this.arn
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnet_ids
  listener_arn = aws_lb_listener.this.arn

  alb_security_group_id    = aws_security_group.alb.id
  extra_security_group_ids = [aws_security_group.app.id]
  # No DATABASE_URL secret: libpq fills an empty URL from PG* variables, and ECS injects the
  # user and password straight from the RDS-managed secret's JSON keys. Same code as locally.
  environment = { DATABASE_URL = "postgresql://", PGHOST = module.db.address, PGDATABASE = "ai4all", PGSSLMODE = "require" }
  secrets = {
    ANTHROPIC_API_KEY = aws_secretsmanager_secret.anthropic.arn
    PGUSER            = "${module.db.master_secret_arn}:username::"
    PGPASSWORD        = "${module.db.master_secret_arn}:password::"
  }
}