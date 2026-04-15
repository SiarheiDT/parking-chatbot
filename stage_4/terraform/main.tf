terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = var.docker_host
}

resource "docker_image" "stage4_service" {
  name         = var.stage4_image
  keep_locally = true
}

resource "docker_container" "stage4_service" {
  name  = var.stage4_container_name
  image = docker_image.stage4_service.image_id

  restart = "unless-stopped"

  ports {
    internal = 9292
    external = var.stage4_port
  }

  env = [
    "STAGE3_MCP_ENABLED=${var.stage3_mcp_enabled}",
    "STAGE3_MCP_ENDPOINT=${var.stage3_mcp_endpoint}",
    "STAGE3_MCP_API_KEY=${var.stage3_mcp_api_key}",
    "STAGE3_MCP_TIMEOUT_SECONDS=${var.stage3_mcp_timeout_seconds}",
  ]

  command = [
    "uvicorn",
    "app.stage4.service:app",
    "--host",
    "0.0.0.0",
    "--port",
    "9292",
  ]
}
