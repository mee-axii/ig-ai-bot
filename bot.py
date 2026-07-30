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
        await update.message.reply_text("Matn yozing. Masalan: /makevideo AI serial matni...")
        return

    text = " ".join(msg_args)
    status_msg = await update.message.reply_text("🎬 Video yasalmoqda...")

    audio_file = "voice.mp3"
    video_file = "ai_video.mp4"

    try:
        tts = gTTS(text=text, lang='uz')
        tts.save(audio_file)

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', 'color=c=101026:s=1080x1920:r=24',
            '-i', audio_file,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', video_file
        ]
        
        subprocess.run(cmd, check=True)

        with open(video_file, 'rb') as video:
            await update.message.reply_video(video=video, caption="✨ Videongiz tayyor!")
        
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
