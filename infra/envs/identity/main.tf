# identity: the Cognito user pool for the client chat (episode 7).
#
# Long-lived on purpose. prod is destroyed daily (scripts/prod_down.sh); a pool destroyed with it
# would lose every user and get new IDs each day. Apply this once, by hand, before prod reads it:
#   cd infra/envs/identity
#   terraform init -backend-config="bucket=ai4all-tf-state-$(aws sts get-caller-identity --query Account --output text)"
#   terraform apply
# prod reads the outputs through terraform_remote_state; web/.env.local and .env take them too.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    key          = "identity/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = { project = "ai4all", env = "shared" }
  }
}

module "clients" {
  source = "../../modules/cognito"
  name   = "ai4all-clients"
}

output "user_pool_id" { value = module.clients.user_pool_id }
output "web_client_id" { value = module.clients.web_client_id }
