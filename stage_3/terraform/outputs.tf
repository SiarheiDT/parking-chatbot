output "stage3_container_name" {
  description = "Stage 3 MCP container name"
  value       = docker_container.stage3_mcp.name
}

output "stage3_url" {
  description = "Stage 3 MCP service URL"
  value       = "http://localhost:${var.stage3_port}"
}
