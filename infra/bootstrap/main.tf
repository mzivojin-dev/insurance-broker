# Run once by hand with admin credentials (episode 3):
#   cd infra/bootstrap && terraform init && terraform apply -var github_repo=<owner>/<repo>
# Creates the state bucket, the GitHub OIDC provider and the roles the workflows assume.
# Copy the outputs into the repo's Actions variables.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_repo" {
  type        = string
  description = "owner/name of the GitHub repository"
}

data "aws_caller_identity" "me" {}

resource "aws_s3_bucket" "tf_state" {
  bucket = "ai4all-tf-state-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

locals {
  roles = {
    # role name      = which GitHub refs may assume it
    # No staging role: pre-prod testing runs on the local Docker stack (docker-compose.yml),
    # in CI and on laptops, so the only AWS environment is production.
    "gha-plan"        = ["repo:${var.github_repo}:pull_request"]
    "gha-prod-deploy" = ["repo:${var.github_repo}:environment:production"]
  }
}

data "aws_iam_policy_document" "trust" {
  for_each = local.roles
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = each.value
    }
  }
}

resource "aws_iam_role" "gha" {
  for_each           = local.roles
  name               = each.key
  assume_role_policy = data.aws_iam_policy_document.trust[each.key].json
}

resource "aws_iam_role_policy_attachment" "plan_read_only" {
  role       = aws_iam_role.gha["gha-plan"].name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# TODO (episode 3): replace PowerUserAccess with least-privilege policies once the stack settles.
resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.gha["gha-prod-deploy"].name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}

output "AWS_PLAN_ROLE_ARN" { value = aws_iam_role.gha["gha-plan"].arn }
output "AWS_PROD_DEPLOY_ROLE_ARN" { value = aws_iam_role.gha["gha-prod-deploy"].arn }
output "TF_STATE_BUCKET" { value = aws_s3_bucket.tf_state.bucket }
