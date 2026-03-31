variable "docker_host" {
  description = "Docker daemon socket for local Terraform deployment."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "weaviate_image" {
  description = "Weaviate Docker image."
  type        = string
  default     = "cr.weaviate.io/semitechnologies/weaviate:1.36.6"
}

variable "weaviate_container_name" {
  description = "Name of the local Weaviate container."
  type        = string
  default     = "parking_weaviate"
}

variable "weaviate_volume_name" {
  description = "Docker volume name for Weaviate persistence."
  type        = string
  default     = "parking_weaviate_data"
}

variable "weaviate_http_port" {
  description = "External HTTP port for Weaviate."
  type        = number
  default     = 8081
}

variable "weaviate_grpc_port" {
  description = "External gRPC port for Weaviate."
  type        = number
  default     = 50051
}