"""
Instagram AI Agent - Telegram Bot
==================================
Bu bot orqali siz:
  /stats      - Instagram akkauntingiz statistikasini ko'rasiz
  /makevideo  - Matn asosida oddiy video yaratasiz (rasm+matn+ovoz)
  /post       - Yaratilgan videoni Instagramga joylaysiz
  /auto       - Statistikaga qarab avtomatik mavzu tanlab, video yaratib, joylaydi

Barcha sozlamalar .env faylida yoki Render "Environment" bo'limida turadi.
"""

import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from instagram import get_account_stats, post_video_to_instagram
from video import create_simple_video
from uploader import upload_video_and_get_url

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_TELEGRAM_USER_ID")  # faqat sizga javob berishi uchun

# Oxirgi yaratilgan videoni vaqtincha saqlab turish uchun (oddiy xotira)
LAST_VIDEO_PATH = {"path": None}


def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_ID:
        return True  # agar sozlanmagan bo'lsa, hammaga ochiq (tavsiya etilmaydi)
    return str(update.effective_user.id) == str(ALLOWED_USER_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men Instagram AI agentingizman.\n\n"
        "Buyruqlar:\n"
        "/stats - statistikani ko'rish\n"
        "/makevideo <matn> - video yaratish\n"
        "/post - oxirgi videoni Instagramga joylash\n"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text("Statistika olinmoqda...")
    try:
        data = get_account_stats()
        text = (
            f"📊 Instagram statistikasi:\n\n"
            f"Followers: {data.get('followers_count', 'N/A')}\n"
            f"Postlar soni: {data.get('media_count', 'N/A')}\n"
            f"Oxirgi post ta'siri (reach): {data.get('last_reach', 'N/A')}\n"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("stats xatolik")
        await update.message.reply_text(f"Xatolik: {e}")


async def makevideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("Foydalanish: /makevideo Bugungi mavzu haqida matn")
        return

    await update.message.reply_text("Video yaratilmoqda, biroz kuting...")
    try:
        path = create_simple_video(text)
        LAST_VIDEO_PATH["path"] = path
        await update.message.reply_video(video=open(path, "rb"))
        await update.message.reply_text(
            "Video tayyor. Instagramga joylash uchun /post buyrug'ini yuboring."
        )
    except Exception as e:
        logger.exception("makevideo xatolik")
        await update.message.reply_text(f"Video yaratishda xatolik: {e}")


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    path = LAST_VIDEO_PATH.get("path")
    if not path or not os.path.exists(path):
        await update.message.reply_text("Avval /makevideo bilan video yarating.")
        return

    await update.message.reply_text("Video yuklanmoqda va Instagramga joylanmoqda, biroz kuting...")
    try:
        public_url = upload_video_and_get_url(path)
        result = post_video_to_instagram(public_url, caption="AI tomonidan yaratilgan video 🎬")
        await update.message.reply_text(f"Joylandi! Post ID: {result}")
    except Exception as e:
        logger.exception("post xatolik")
        await update.message.reply_text(f"Joylashda xatolik: {e}")


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistikani tekshiradi, oddiy mavzu tanlaydi, video yaratadi va joylaydi."""
    if not is_authorized(update):
        return
    topic = " ".join(context.args) if context.args else "Bugungi kunning eng qiziq fikri"

    await update.message.reply_text("Tahlil qilinmoqda...")
    try:
        data = get_account_stats()
    except Exception as e:
        await update.message.reply_text(f"Statistikani olishda xatolik: {e}")
        return

    await update.message.reply_text(
        f"Followers: {data.get('followers_count', 'N/A')}. Video yaratilmoqda..."
    )
    try:
        path = create_simple_video(topic)
        LAST_VIDEO_PATH["path"] = path
        await update.message.reply_video(video=open(path, "rb"))
    except Exception as e:
        await update.message.reply_text(f"Video yaratishda xatolik: {e}")
        return

    await update.message.reply_text("Instagramga joylanmoqda...")
    try:
        public_url = upload_video_and_get_url(path)
        result = post_video_to_instagram(public_url, caption=topic)
        await update.message.reply_text(f"Tayyor! Post ID: {result}")
    except Exception as e:
        await update.message.reply_text(f"Joylashda xatolik: {e}")


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
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("makevideo", makevideo))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("auto", auto))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
