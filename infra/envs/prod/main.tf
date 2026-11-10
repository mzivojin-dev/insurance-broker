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

# TODO (episode 3): wire up the modules; pass var.ephemeral to db and services
# module "vpc"      { source = "../../modules/vpc" }
# module "db"       { source = "../../modules/rds_pgvector", ephemeral = var.ephemeral ... }
# module "services" {
#   source    = "../../modules/ecs_service"
#   for_each  = toset(local.agents)
#   name      = each.key
#   image_tag = var.image_tag
# }
