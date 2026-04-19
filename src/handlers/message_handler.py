"""
Handler untuk pesan teks biasa (bukan command).
Di sinilah alur utama chat dengan AI terjadi.
"""

import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.ai.client import ai_client, AIAllModelsFailedError
from src.utils.history import conversation_history
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _detect_role(text: str) -> str:
    """
    Pilih role model berdasarkan panjang pesan user.

    Logika:
      < 50 karakter   → "fast"     (sapaan, pesan pendek)
      < 300 karakter  → "balanced" (percakapan umum)
      >= 300 karakter → "smart"    (pertanyaan panjang & kompleks)
    """
    if len(text) < 20:
        return "fast"
    elif len(text) < 200:
        return "balanced"
    else:
        return "smart"


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.sleep(4)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_message = update.message.text

    logger.info("message_received", user_id=user.id, username=user.username, chars=len(user_message))

    conversation_history.add(user.id, "user", user_message)
    history = conversation_history.get(user.id)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context, chat_id, stop_typing))

    try:
        role = _detect_role(user_message)
        logger.info("role_selected", role=role, chars=len(user_message))
        response_text, model_used = await ai_client.chat(messages=history, role=role)

        conversation_history.add(user.id, "assistant", response_text)
        logger.info("message_answered", user_id=user.id, model_used=model_used)

        await update.message.reply_text(response_text)

    except AIAllModelsFailedError as e:
        logger.error("all_models_failed", user_id=user.id, error=str(e))
        conversation_history.clear(user.id)
        await update.message.reply_text(
            "⚠️ Maaf, semua model AI sedang tidak tersedia. "
            "Silakan coba beberapa menit lagi.\n\n"
            "_Riwayat percakapan telah direset untuk percobaan berikutnya._",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error("unexpected_error", user_id=user.id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Terjadi kesalahan tidak terduga. Silakan coba lagi.")

    finally:
        stop_typing.set()
        typing_task.cancel()