from telegram import Update
from telegram.ext import ContextTypes
from src.utils.history import conversation_history
from src.utils.logger import get_logger
from config.models import AI_MODELS

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    models_list = "\n".join(
        f"  {i+1}. {m.display_name} ({m.provider})"
        for i, m in enumerate(AI_MODELS)
    )

    await update.message.reply_text(
        f"👋 Halo, {user.first_name}!\n\n"
        f"🤖 *Model AI (urutan prioritas):*\n{models_list}\n\n"
        f"*Commands:*\n"
        f"/help — Bantuan\n"
        f"/clear — Hapus riwayat\n"
        f"/status — Cek status",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Cara Penggunaan:*\n\n"
        "• Kirim pesan biasa → dijawab AI\n"
        "• Bot ingat konteks percakapanmu\n"
        "• Jika satu AI error → otomatis pindah ke cadangan\n\n"
        "*Commands:*\n"
        "/start /help /clear /status",
        parse_mode="Markdown",
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = conversation_history.count(user_id)
    conversation_history.clear(user_id)
    await update.message.reply_text(f"🗑️ Riwayat dihapus ({count} pesan). Mulai dari awal!")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    models_info = "\n".join(
        f"  {'🟢' if i==0 else '🟡'} {m.display_name} — {m.provider}"
        for i, m in enumerate(AI_MODELS)
    )

    await update.message.reply_text(
        f"📊 *Status Bot*\n\n"
        f"*Model:*\n{models_info}\n\n"
        f"*Riwayatmu:* {conversation_history.count(user_id)} pesan",
        parse_mode="Markdown",
    )