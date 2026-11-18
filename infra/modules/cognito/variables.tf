# Module inputs (episode 7)

variable "name" {
  type        = string
  description = "User pool name, e.g. ai4all-clients"
}

variable "deletion_protection" {
  type        = string
  default     = "ACTIVE"
  description = "ACTIVE keeps the pool (and its users) from being destroyed by accident; INACTIVE to allow it"
}
