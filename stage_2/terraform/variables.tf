variable "docker_host" {
  description = "Docker daemon socket for local deployment."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "admin_webhook_image" {
  description = "Container image containing this project code and dependencies."
  type        = string
  default     = "parking-chatbot:latest"
}

variable "admin_webhook_container_name" {
  description = "Docker container name for Stage 2 admin webhook service."
  type        = string
  default     = "parking_admin_webhook"
}

variable "admin_webhook_port" {
  description = "External port mapped to webhook container internal 9090."
  type        = number
  default     = 9090
}

variable "db_path" {
  description = "Database path visible from inside the container."
  type        = string
  default     = "data/db/parking_dev.db"
}

variable "telegram_bot_token" {
  description = "Telegram Bot token for admin notifications and callback API calls."
  type        = string
  sensitive   = true
}

variable "telegram_admin_chat_id" {
  description = "Telegram chat id receiving reservation approval messages."
  type        = string
}

variable "telegram_webhook_secret" {
  description = "Secret path segment required by POST /telegram/webhook/{secret}."
  type        = string
  sensitive   = true
}

variable "telegram_api_base" {
  description = "Optional Telegram API base URL override."
  type        = string
  default     = ""
}

variable "stage2_admin_handler" {
  description = "Decision handler mode: direct or langchain_tools."
  type        = string
  default     = "direct"
}

variable "model_name" {
  description = "Default model name used by app config."
  type        = string
  default     = "gpt-4o-mini"
}

variable "openai_api_key" {
  description = "OpenAI API key, required when stage2_admin_handler=langchain_tools."
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_agent_model" {
  description = "Optional explicit model for Stage 2 admin LangChain agent."
  type        = string
  default     = ""
}
