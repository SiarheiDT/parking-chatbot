"""Outbound notifications (Stage 2 admin channel, etc.)."""

from app.notifications.telegram import (
    notify_admin_new_reservation,
    send_telegram_message,
    telegram_is_configured,
)

__all__ = [
    "notify_admin_new_reservation",
    "send_telegram_message",
    "telegram_is_configured",
]
