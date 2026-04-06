output "admin_webhook_container_name" {
  description = "Name of Stage 2 admin webhook container."
  value       = docker_container.admin_webhook.name
}

output "admin_webhook_url" {
  description = "Local URL for Stage 2 admin webhook service."
  value       = "http://localhost:${var.admin_webhook_port}"
}

output "admin_webhook_secret_path" {
  description = "Webhook callback path configured for Telegram setWebhook."
  value       = "/telegram/webhook/${var.telegram_webhook_secret}"
  sensitive   = true
}

output "stage2_admin_handler" {
  description = "Configured decision path for admin actions."
  value       = var.stage2_admin_handler
}
