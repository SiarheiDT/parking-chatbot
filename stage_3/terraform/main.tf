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

resource "docker_image" "stage3_mcp" {
  name         = var.stage3_image
  keep_locally = true
}

resource "docker_container" "stage3_mcp" {
  name  = var.stage3_container_name
  image = docker_image.stage3_mcp.image_id

  restart = "unless-stopped"

  ports {
    internal = 9191
    external = var.stage3_port
  }

  env = [
    "STAGE3_MCP_API_KEY=${var.stage3_mcp_api_key}",
    "STAGE3_MCP_OUTPUT_FILE=${var.stage3_output_file}",
  ]

  command = [
    "uvicorn",
    "app.stage3.mcp_server:app",
    "--host",
    "0.0.0.0",
    "--port",
    "9191",
  ]
}
