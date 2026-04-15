output "stage4_container_name" {
  description = "Stage 4 container name"
  value       = docker_container.stage4_service.name
}

output "stage4_url" {
  description = "Stage 4 service URL"
  value       = "http://localhost:${var.stage4_port}"
}
