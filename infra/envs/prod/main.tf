# prod environment. Filled in during episode 3 from the modules in infra/modules.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket       = "ai4all-tf-state-REPLACE_WITH_ACCOUNT_ID" # TF_STATE_BUCKET from infra/bootstrap
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

locals {
  agents = ["client_service", "submission_intake", "book_analyst"]
}

module "vpc" {
  source = "../../modules/vpc"
  env    = "prod"
  region = "us-east-1"
}

resource "aws_ecs_cluster" "this" { name = "ai4all-prod" }
resource "aws_s3_bucket" "docs" {
  bucket        = "ai4all-prod-docs-${data.aws_caller_identity.me.account_id}"
  force_destroy = var.ephemeral
}

module "db" {
  source                     = "../../modules/rds_pgvector"
  env                        = "prod"
  ephemeral                  = var.ephemeral
  vpc_id                     = module.vpc.vpc_id
  db_subnet_group            = module.vpc.db_subnet_group
  allowed_security_group_ids = [for s in module.services : s.security_group_id]
}

module "services" {
  source       = "../../modules/ecs_service"
  for_each     = toset(local.agents)
  name         = each.key
  env          = "prod"
  ephemeral    = var.ephemeral
  image_tag    = var.image_tag
  cluster_arn  = aws_ecs_cluster.this.arn
  subnet_ids   = module.vpc.private_subnet_ids
  listener_arn = aws_lb_listener.https.arn
  # No DATABASE_URL secret: libpq fills an empty URL from PG* variables, and ECS injects the
  # user and password straight from the RDS-managed secret's JSON keys. Same code as locally.
  environment  = { DATABASE_URL = "postgresql://", PGHOST = module.db.address, PGDATABASE = "ai4all", PGSSLMODE = "require" }
  secrets = {
    ANTHROPIC_API_KEY = aws_secretsmanager_secret.anthropic.arn
    PGUSER            = "${module.db.master_secret_arn}:username::"
    PGPASSWORD        = "${module.db.master_secret_arn}:password::"
  }
}