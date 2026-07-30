"""
Oddiy video generatsiya moduli.

Bu to'liq bepul ishlaydi - hech qanday pullik AI video API kerak emas:
  1. Matnni ovozga aylantiradi (gTTS - bepul Google Text-to-Speech)
  2. Fon rasmini yaratadi (matn shu rasm ustiga chiqadi)
  3. ffmpeg orqali rasm + ovozdan video yig'adi

Sifat "Sora/Runway" darajasida emas, lekin butunlay bepul va
Reels/Shorts formatiga (9:16) mos.
"""

import os
import uuid
import textwrap
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import subprocess

OUTPUT_DIR = "/tmp/ig_bot_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 1080, 1920  # Reels o'lchami (9:16)


def _make_background_image(text: str, out_path: str):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 20, 30))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64
        )
    except Exception:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(text, width=22)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    position = ((WIDTH - text_w) / 2, (HEIGHT - text_h) / 2)

    draw.multiline_text(
        position, wrapped, font=font, fill=(255, 255, 255), align="center"
    )
    img.save(out_path)


def create_simple_video(text: str) -> str:
    """Matndan Reels formatidagi video yaratadi va yo'lini qaytaradi."""
    session_id = str(uuid.uuid4())[:8]
    image_path = os.path.join(OUTPUT_DIR, f"{session_id}.png")
    audio_path = os.path.join(OUTPUT_DIR, f"{session_id}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"{session_id}.mp4")

    # 1. Fon rasmi
    _make_background_image(text, image_path)

    # 2. Ovoz (gTTS o'zbek tilini to'liq qo'llab-quvvatlamasligi mumkin,
    #    shu sabab standart "ru" yoki "en" ga tushishi mumkin - kerak bo'lsa
    #    boshqa TTS xizmatiga almashtirish mumkin)
    tts = gTTS(text=text, lang="ru")
    tts.save(audio_path)

    # 3. ffmpeg orqali video yig'ish (rasm statik, ovoz uzunligiga moslanadi)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        video_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    return video_path
