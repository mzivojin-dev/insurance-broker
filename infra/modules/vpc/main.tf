module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name               = "ai4all-${var.env}"
  cidr               = "10.20.0.0/16"
  azs                = ["${var.region}a", "${var.region}b"]
  public_subnets     = ["10.20.0.0/24", "10.20.1.0/24"]
  private_subnets    = ["10.20.10.0/24", "10.20.11.0/24"]
  database_subnets   = ["10.20.20.0/24", "10.20.21.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true   # about $32/month; say this number on camera
}

output "vpc_id"             { value = module.vpc.vpc_id }
output "private_subnet_ids" { value = module.vpc.private_subnets }
output "public_subnet_ids"  { value = module.vpc.public_subnets }
output "db_subnet_group"    { value = module.vpc.database_subnet_group_name }