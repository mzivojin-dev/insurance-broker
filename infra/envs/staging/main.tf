# staging environment. Filled in during episode 3 from the modules in infra/modules.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket       = "ai4all-tf-state-REPLACE_WITH_ACCOUNT_ID" # TF_STATE_BUCKET from infra/bootstrap
    key          = "staging/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { project = "ai4all", env = "staging" }
  }
}

variable "image_tag" {
  type        = string
  description = "Git SHA of the images to run; set by deploy.yml"
  default     = "latest"
}

locals {
  agents = ["client_service", "submission_intake", "book_analyst"]
}

# TODO (episode 3): wire up the modules
# module "vpc"      { source = "../../modules/vpc" }
# module "db"       { source = "../../modules/rds_pgvector" ... }
# module "services" {
#   source    = "../../modules/ecs_service"
#   for_each  = toset(local.agents)
#   name      = each.key
#   image_tag = var.image_tag
# }
