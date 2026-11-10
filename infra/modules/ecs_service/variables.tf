variable "name" {
  type        = string
  description = "agent name; also the ALB path prefix /<name>/*"
}

variable "env" { type = string }

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "ephemeral" {
  type        = bool
  description = "true: ECR repo is deleted even with images in it, logs kept 1 day"
}

variable "image_tag" { type = string }
variable "cluster_arn" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "listener_arn" { type = string }

variable "alb_security_group_id" {
  type        = string
  description = "only the load balancer may reach the tasks on 8080"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "environment" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  type        = map(string)
  default     = {}
  description = "env var name -> Secrets Manager ARN, optionally with a JSON key (<arn>:key::)"
}

variable "extra_security_group_ids" {
  type        = list(string)
  default     = []
  description = "more groups for the tasks, e.g. the one the database trusts"
}
