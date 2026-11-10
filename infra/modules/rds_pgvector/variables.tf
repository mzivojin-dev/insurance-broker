variable "env" { type = string }

variable "ephemeral" {
  type        = bool
  description = "true: no deletion protection, no backups, no final snapshot (prod is destroyed daily)"
}

variable "vpc_id" { type = string }
variable "db_subnet_group" { type = string }

variable "allowed_security_group_ids" {
  type        = list(string)
  description = "security groups allowed to reach Postgres on 5432 (the ECS tasks)"
}
