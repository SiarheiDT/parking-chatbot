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

resource "docker_image" "admin_webhook" {
  name         = var.admin_webhook_image
  keep_locally = true
}

resource "docker_container" "admin_webhook" {
  name  = var.admin_webhook_container_name
  image = docker_image.admin_webhook.image_id

  restart = "unless-stopped"

  ports {
    internal = 9090
    external = var.admin_webhook_port
  }

  env = concat(
    [
      "DB_PATH=${var.db_path}",
      "TELEGRAM_BOT_TOKEN=${var.telegram_bot_token}",
      "TELEGRAM_ADMIN_CHAT_ID=${var.telegram_admin_chat_id}",
      "TELEGRAM_WEBHOOK_SECRET=${var.telegram_webhook_secret}",
      "STAGE2_ADMIN_HANDLER=${var.stage2_admin_handler}",
      "MODEL_NAME=${var.model_name}",
    ],
    var.telegram_api_base != "" ? ["TELEGRAM_API_BASE=${var.telegram_api_base}"] : [],
    var.openai_api_key != "" ? ["OPENAI_API_KEY=${var.openai_api_key}"] : [],
    var.admin_agent_model != "" ? ["ADMIN_AGENT_MODEL=${var.admin_agent_model}"] : []
  )

  command = [
    "uvicorn",
    "app.stage2.webhook_app:app",
    "--host",
    "0.0.0.0",
    "--port",
    "9090",
  ]
}
