import traceback
from telegram import Update
from telegram.ext import ContextTypes
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Didaftarkan di main.py via app.add_error_handler().
    Dipanggil otomatis oleh framework jika ada exception
    yang tidak tertangani di handler manapun.
    """
    logger.error(
        "unhandled_telegram_error",
        error=str(context.error),
        traceback=traceback.format_exc(),
        update=str(update)[:200] if update else None,
    )

    # Coba balas user jika masih bisa
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan internal. Mohon coba lagi."
            )
        except Exception:
            pass  # Abaikan jika tidak bisa reply