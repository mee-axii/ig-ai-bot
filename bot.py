import os
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from gTTS import gTTS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_TELEGRAM_USER_ID")

async def make_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        return

    msg_args = context.args
    if not msg_args:
        await update.message.reply_text("Iltimos, matn yozing. Masalan: /makevideo AI serial uchun matn...")
        return

    text = " ".join(msg_args)
    status_msg = await update.message.reply_text("🎬 Ovozli video yasalmoqda...")

    audio_file = "voice.mp3"
    video_file = "ai_video.mp4"

    try:
        # 1. Matnni ovozga aylantirish
        tts = gTTS(text=text, lang='uz')
        tts.save(audio_file)

        # 2. Faqat fon va ovozdan iborat toza video yasash (Subtitrsiz)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'color=c=101026:s=1080x1920:r=24', # Reels o'lchami
            '-i', audio_file,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', video_file
        ]
        
        subprocess.run(cmd, check=True)

        # 3. Yuborish
        with open(video_file, 'rb') as video:
            await update.message.reply_video(video=video, caption="✨ Videongiz tayyor! Endi uni istalgan ilovada bezashingiz mumkin.")
        
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")
    finally:
        if os.path.exists(audio_file): os.remove(audio_file)
        if os.path.exists(video_file): os.remove(video_file)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("makevideo", make_video))
    app.run_polling()

if __name__ == "__main__":
    main()
