variable "env" { type = string }

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "ephemeral" {
  type        = bool
  description = "true: logs kept 1 day; traces live on the task's own disk and go with it"
}

variable "image" {
  type        = string
  description = "keep in step with the phoenix service in docker-compose.yml"
  default     = "arizephoenix/phoenix:version-21.0.0"
}

variable "cluster_arn" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "listener_arn" { type = string }

variable "alb_security_group_id" {
  type        = string
  description = "the load balancer may reach the UI on 6006 under /phoenix"
}

variable "client_security_group_ids" {
  type        = list(string)
  description = "groups whose tasks may send traces to 6006 directly (the agents)"
}

variable "secret_arn" {
  type        = string
  description = <<-EOT
    Secrets Manager secret with JSON keys secret, admin_secret, admin_password
    (PHOENIX_SECRET, PHOENIX_ADMIN_SECRET, PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD).
  EOT
}
