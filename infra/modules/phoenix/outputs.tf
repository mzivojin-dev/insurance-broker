output "collector_endpoint" {
  description = "PHOENIX_COLLECTOR_ENDPOINT for the agents (inside the VPC)"
  value       = "http://${aws_service_discovery_service.this.name}.${aws_service_discovery_private_dns_namespace.this.name}:${local.port}"
}

output "root_path" { value = local.root_path }
output "service_name" { value = aws_ecs_service.this.name }
