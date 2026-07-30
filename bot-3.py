"""
AI Video Bot - Telegram orqali
================================
Bu bot orqali siz:
  /makevideo <matn>  - Matn asosida sifatli video yaratasiz (rasm+ovoz+effekt)

Video tayyor bo'lgach, Telegram orqali sizga yuboriladi.
Instagramga joylash - o'zingiz, video faylni saqlab, Reels sifatida yuklaysiz.

Barcha sozlamalar Render "Environment" bo'limida turadi.
"""

import os
import logging
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from video import create_simple_video

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_TELEGRAM_USER_ID")  # faqat sizga javob berishi uchun

KNOWN_LANG_CODES = {"ru", "en", "tr"}


def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_ID:
        return True  # agar sozlanmagan bo'lsa, hammaga ochiq (tavsiya etilmaydi)
    return str(update.effective_user.id) == str(ALLOWED_USER_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("Kechirasiz, bu bot faqat egasiga xizmat qiladi.")
        return
    await update.message.reply_text(
        "Salom! Men video yaratuvchi AI agentingizman.\n\n"
        "Foydalanish:\n"
        "/makevideo <matn> - video yaratish\n"
        "Masalan: /makevideo Bugun ajoyib kun, hammaga zoʻr kayfiyat tilayman\n\n"
        "Ixtiyoriy: ovoz tilini tanlash uchun birinchi so'z sifatida yozing "
        "(ru / en / tr), aks holda avtomatik ruscha ovoz tanlanadi.\n"
        "Masalan: /makevideo en Good morning everyone"
    )


async def makevideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Foydalanish: /makevideo Bugungi mavzu haqida matn\n"
            "(ixtiyoriy til bilan: /makevideo en Your text here)"
        )
        return

    preferred_lang = None
    if args[0].lower() in KNOWN_LANG_CODES:
        preferred_lang = args[0].lower()
        text = " ".join(args[1:])
    else:
        text = " ".join(args)

    if not text.strip():
        await update.message.reply_text("Matn bo'sh bo'lmasligi kerak.")
        return

    if len(text) > 400:
        await update.message.reply_text(
            "Matn juda uzun (400 belgidan oshmasligi kerak), qisqartirib qayta yuboring."
        )
        return

    status_msg = await update.message.reply_text("🎬 Video yaratilmoqda, biroz kuting (20-40 soniya)...")

    try:
        path = create_simple_video(text, preferred_lang=preferred_lang)
    except Exception as e:
        logger.error(f"Video yaratishda xatolik: {traceback.format_exc()}")
        await status_msg.edit_text(
            f"❌ Video yaratishda xatolik yuz berdi.\n\nSabab: {e}\n\n"
            "Qaytadan urinib ko'ring, agar xatolik takrorlansa, matnni qisqartirib ko'ring."
        )
        return

    try:
        with open(path, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Video tayyor! Instagram/Reels'ga o'zingiz yuklashingiz mumkin.",
                supports_streaming=True,
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Videoni yuborishda xatolik: {traceback.format_exc()}")
        await status_msg.edit_text(f"❌ Video yaratildi, lekin yuborishda xatolik: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bu buyruqni tushunmadim. /start yozing.")


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti")

    def log_message(self, *args):
        pass  # konsolni chalkashtirmaslik uchun log chiqarmaydi


def _run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    server.serve_forever()


def main():
    # Render bepul "Web Service" biror portni tinglashni talab qiladi,
    # shuning uchun alohida oqimda (thread) oddiy server ishga tushiramiz.
    threading.Thread(target=_run_health_server, daemon=True).start()

    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment o'zgaruvchisi topilmadi")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("makevideo", makevideo))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
