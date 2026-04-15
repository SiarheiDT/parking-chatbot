variable "docker_host" {
  description = "Docker daemon socket"
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "stage3_image" {
  description = "Image with project code and dependencies"
  type        = string
  default     = "parking-chatbot:latest"
}

variable "stage3_container_name" {
  description = "Stage 3 MCP container name"
  type        = string
  default     = "parking_stage3_mcp"
}

variable "stage3_port" {
  description = "External port for Stage 3 MCP service"
  type        = number
  default     = 9191
}

variable "stage3_mcp_api_key" {
  description = "API key required by MCP endpoint"
  type        = string
  sensitive   = true
}

variable "stage3_output_file" {
  description = "Output file path as visible inside container"
  type        = string
  default     = "data/processed/confirmed_reservations.txt"
}
