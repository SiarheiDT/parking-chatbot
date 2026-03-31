output "weaviate_container_name" {
  description = "Name of the Weaviate container."
  value       = docker_container.weaviate.name
}

output "weaviate_http_url" {
  description = "HTTP endpoint of the Weaviate instance."
  value       = "http://localhost:${var.weaviate_http_port}"
}

output "weaviate_grpc_endpoint" {
  description = "gRPC endpoint of the Weaviate instance."
  value       = "localhost:${var.weaviate_grpc_port}"
}

output "weaviate_volume_name" {
  description = "Docker volume used by Weaviate."
  value       = docker_volume.weaviate_data.name
}