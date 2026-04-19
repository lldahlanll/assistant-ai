"""
Entry point bot Telegram.
Jalankan dengan: python main.py
"""

import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import settings
from src.handlers import (
    start_command, help_command,
    clear_command, status_command,
    message_handler,
)
from src.middlewares.error_handler import global_error_handler
from src.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def build_application() -> Application:
    """Buat dan konfigurasi aplikasi Telegram bot."""
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # ── Command Handlers ─────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("status", status_command))

    # ── Message Handler (teks biasa) ──────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    # ── Global Error Handler ──────────────────────
    app.add_error_handler(global_error_handler)

    return app


def main() -> None:
    """Mulai bot."""
    setup_logging()
    logger.info("bot_starting", env=settings.app_env, log_level=settings.log_level)

    app = build_application()
    logger.info("bot_polling_started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()