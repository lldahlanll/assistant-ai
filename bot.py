import os
import json
import logging
import asyncio
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)

load_dotenv()
SHOW_TRANSCRIPT = os.getenv("SHOW_TRANSCRIPT", "true").lower() == "true"
BOT_PERSON = os.getenv("BOT_PERSONA", "Kamu adalah Ephinu, asisten AI pribadi yang helpful dan ramah. Jangan pernah mengaku sebagai Gemini atau produk Google manapun.")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

HISTORY_DIR = Path("chat_history")
HISTORY_DIR.mkdir(exist_ok=True)

sessions: dict[int, list] = {}
executor = ThreadPoolExecutor(max_workers=4)

# ── Helper: history ──────────────────────────────────────────

def get_history_file(user_id: int) -> Path:
    return HISTORY_DIR / f"{user_id}.json"

def load_history(user_id: int) -> list:
    f = get_history_file(user_id)
    if f.exists():
        with open(f) as fp:
            return json.load(fp)
    return []

def save_history(user_id: int, history: list):
    with open(get_history_file(user_id), "w") as fp:
        json.dump(history, fp, ensure_ascii=False, indent=2)

def get_session(user_id: int) -> list:
    if user_id not in sessions:
        sessions[user_id] = load_history(user_id)
    return sessions[user_id]

def build_contents(history: list) -> list[types.Content]:
    contents = []
    for h in history:
        # Pesan teks biasa
        if h.get("type", "text") == "text":
            contents.append(types.Content(
                role=h["role"],
                parts=[types.Part(text=h["text"])]
            ))
        # Pesan gambar (disimpan sebagai base64)
        elif h.get("type") == "image":
            parts = []
            if h.get("caption"):
                parts.append(types.Part(text=h["caption"]))
            parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type=h["mime_type"],
                    data=h["data"]  # base64 string
                )
            ))
            contents.append(types.Content(role=h["role"], parts=parts))
    return contents

# ── Gemini calls (blocking, dijalankan di executor) ──────────

def call_gemini_text(history: list) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=build_contents(history),
        config=types.GenerateContentConfig(
            system_instruction=BOT_PERSON,
            max_output_tokens=2048,
        )
    )
    return response.text

def call_gemini_with_image(image_bytes: bytes, mime_type: str, caption: str, history: list) -> str:
    """Kirim gambar + caption + history ke Gemini."""
    import base64

    # Bangun contents dari history lama
    contents = build_contents(history)

    # Tambahkan pesan baru dengan gambar
    parts = []
    if caption:
        parts.append(types.Part(text=caption))
    parts.append(types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=image_bytes)
    ))
    contents.append(types.Content(role="user", parts=parts))

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=BOT_PERSON,
            max_output_tokens=2048,
        )
    )
    return response.text

def transcribe_audio(audio_path: str) -> str:
    """Transkripsi audio menggunakan Gemini."""
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(role="user", parts=[
                types.Part(
                    inline_data=types.Blob(
                        mime_type="audio/ogg",
                        data=audio_bytes
                    )
                ),
                types.Part(text="Tolong transkripkan audio ini menjadi teks. Hanya tampilkan teks transkripsi saja tanpa komentar tambahan.")
            ])
        ]
    )
    return response.text.strip()

# ── Typing loop ──────────────────────────────────────────────

async def typing_loop(context: ContextTypes.DEFAULT_TYPE, chat_id: int, stop_event: asyncio.Event):
    while not stop_event.is_set():
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=4)
        except asyncio.TimeoutError:
            pass

# ── Handlers ─────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Halo {user.first_name}! 👋\n"
        "Saya adalah AI Assistant powered by Gemini.\n\n"
        "Yang bisa saya lakukan:\n"
        "💬 Chat teks biasa\n"
        "🖼️ Analisis gambar (kirim foto + pertanyaan)\n"
        "🎤 Voice message (kirim pesan suara)\n\n"
        "Perintah:\n"
        "/start - Mulai\n"
        "/clear - Hapus riwayat percakapan\n"
        "/help - Bantuan"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in sessions:
        del sessions[user_id]
    history_file = get_history_file(user_id)
    if history_file.exists():
        history_file.unlink()
    await update.message.reply_text("✅ Riwayat percakapan telah dihapus!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Gemini AI Bot*\n\n"
        "💬 *Teks* — Ketik pertanyaan apa saja\n"
        "🖼️ *Gambar* — Kirim foto, bisa dengan caption/pertanyaan\n"
        "🎤 *Voice* — Kirim pesan suara, akan ditranskripsi lalu dijawab\n\n"
        "/clear — Hapus riwayat percakapan",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pesan teks."""
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_id = update.effective_chat.id

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context, chat_id, stop_typing))

    try:
        history = get_session(user_id)
        history.append({"role": "user", "type": "text", "text": user_text})

        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(executor, call_gemini_text, history)

        history.append({"role": "model", "type": "text", "text": reply})
        if len(history) > 50:
            history = history[-50:]
            sessions[user_id] = history
        save_history(user_id, history)

        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error teks user {user_id}: {e}")
        await update.message.reply_text("⚠️ Maaf, terjadi kesalahan. Silakan coba lagi.")
    finally:
        stop_typing.set()
        await typing_task

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler gambar/foto."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    caption = update.message.caption or "Tolong analisis gambar ini."

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context, chat_id, stop_typing))

    try:
        # Ambil foto resolusi tertinggi
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download ke memori
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

        with open(tmp_path, "rb") as f:
            image_bytes = f.read()
        os.unlink(tmp_path)

        history = get_session(user_id)

        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(
            executor, call_gemini_with_image,
            image_bytes, "image/jpeg", caption, history
        )

        # Simpan ke history sebagai teks ringkas
        history.append({"role": "user", "type": "text", "text": f"[Mengirim gambar] {caption}"})
        history.append({"role": "model", "type": "text", "text": reply})
        if len(history) > 50:
            history = history[-50:]
            sessions[user_id] = history
        save_history(user_id, history)

        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error foto user {user_id}: {e}")
        await update.message.reply_text("⚠️ Gagal memproses gambar. Silakan coba lagi.")
    finally:
        stop_typing.set()
        await typing_task

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voice message."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context, chat_id, stop_typing))

    try:
        # Download file voice (.ogg)
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

        loop = asyncio.get_event_loop()

        # Step 1: Transkripsi audio
        transcript = await loop.run_in_executor(executor, transcribe_audio, tmp_path)
        os.unlink(tmp_path)

        logging.info(f"Transkripsi user {user_id}: {transcript}")

        # Step 2: Jawab berdasarkan transkripsi
        history = get_session(user_id)
        history.append({"role": "user", "type": "text", "text": transcript})

        reply = await loop.run_in_executor(executor, call_gemini_text, history)

        history.append({"role": "model", "type": "text", "text": reply})
        if len(history) > 50:
            history = history[-50:]
            sessions[user_id] = history
        save_history(user_id, history)

        # Tampilkan transkripsi + jawaban
        if SHOW_TRANSCRIPT:
            await update.message.reply_text(
                f"🎤 *Transkripsi:*\n_{transcript}_\n\n{reply}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"Error voice user {user_id}: {e}")
        await update.message.reply_text("⚠️ Gagal memproses voice message. Silakan coba lagi.")
    finally:
        stop_typing.set()
        await typing_task

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN tidak ditemukan di .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logging.info("✅ Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()