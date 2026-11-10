#!/usr/bin/env bash
# End-of-day teardown: destroy every prod resource so nothing bills overnight.
# Prod is ephemeral (var.ephemeral = true): no deletion protection, no final snapshot,
# S3 and ECR emptied on destroy. Data comes back with the seed job next time.
#
# Usage: scripts/prod_down.sh          # terraform shows the plan and asks "yes"
#        scripts/prod_down.sh --yes    # no prompt
# Needs AWS credentials for the account (aws sso login). Leaves infra/bootstrap alone:
# the state bucket and OIDC roles cost nothing and are needed to deploy again.
set -euo pipefail
cd "$(dirname "$0")/../infra/envs/prod"

approve=()
[[ "${1:-}" == "--yes" ]] && approve=(-auto-approve)

bucket="${TF_STATE_BUCKET:-ai4all-tf-state-$(aws sts get-caller-identity --query Account --output text | tr -d '\r')}"
terraform init -input=false -backend-config="bucket=$bucket" >/dev/null
terraform destroy -input=false "${approve[@]}"

echo
echo "Anything still tagged project=ai4all env=prod (should be empty; deleted items can linger a few minutes):"
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=project,Values=ai4all Key=env,Values=prod \
  --query 'ResourceTagMappingList[].ResourceARN' --output text
