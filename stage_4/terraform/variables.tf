variable "docker_host" {
  description = "Docker daemon socket"
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "stage4_image" {
  description = "Image with project code and dependencies"
  type        = string
  default     = "parking-chatbot:latest"
}

variable "stage4_container_name" {
  description = "Stage 4 service container name"
  type        = string
  default     = "parking_stage4_service"
}

variable "stage4_port" {
  description = "External port for Stage 4 API service"
  type        = number
  default     = 9292
}

variable "stage3_mcp_enabled" {
  description = "Whether Stage 4 should call Stage 3 MCP"
  type        = string
  default     = "true"
}

variable "stage3_mcp_endpoint" {
  description = "Stage 3 MCP endpoint reachable from Stage 4 runtime"
  type        = string
  default     = "http://host.docker.internal:9191/mcp/v1/confirmed-reservations"
}

variable "stage3_mcp_api_key" {
  description = "Stage 3 MCP API key used by Stage 4 service"
  type        = string
  sensitive   = true
}

variable "stage3_mcp_timeout_seconds" {
  description = "Timeout for Stage 3 MCP calls from Stage 4"
  type        = string
  default     = "10"
}
