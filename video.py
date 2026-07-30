"""
Sifatli, xatosiz video yaratish moduli.

- Chiroyli gradient fon
- Matn soyasi bilan (o'qilishi oson bo'lishi uchun)
- Bir necha til uchun ovoz (TTS), avtomatik fallback bilan
- Reels/Shorts formatiga (9:16) mos
- ffmpeg orqali fade-in/fade-out effektlari bilan yig'iladi
"""

import os
import uuid
import textwrap
import subprocess
import logging
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

OUTPUT_DIR = "/tmp/ig_bot_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 1080, 1920  # Reels o'lchami (9:16)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# gTTS urinib ko'radigan tillar tartibi (birinchi ishlagani ishlatiladi)
TTS_LANG_FALLBACK_ORDER = ["ru", "tr", "en"]


def _make_gradient_background() -> Image.Image:
    """Yuqoridan pastga chiroyli to'q ko'k-binafsha gradient yasaydi."""
    top_color = (25, 20, 45)
    bottom_color = (70, 35, 90)

    img = Image.new("RGB", (WIDTH, HEIGHT), color=0)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def _draw_text_with_shadow(draw: ImageDraw.ImageDraw, position, text, font, fill, align):
    x, y = position
    shadow_offset = 4
    # Soya (shadow) - matn ostida, biroz siljigan holda, qorong'i rangda
    draw.multiline_text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0),
        align=align,
    )
    # Asosiy matn
    draw.multiline_text((x, y), text, font=font, fill=fill, align=align)


def _make_background_image(text: str, out_path: str):
    img = _make_gradient_background()

    # Yengil "vinyette" effekt - chekkalarni bироз qorong'ilashtirish
    overlay = Image.new("L", (WIDTH, HEIGHT), 0)
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse(
        [-WIDTH * 0.3, -HEIGHT * 0.2, WIDTH * 1.3, HEIGHT * 1.1], fill=60
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(200))
    dark = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    img = Image.composite(img, dark, overlay)

    draw = ImageDraw.Draw(img)

    # Matn uzunligiga qarab shrift razmerini moslashtiramiz
    length = len(text)
    if length < 60:
        font_size = 78
        wrap_width = 18
    elif length < 150:
        font_size = 62
        wrap_width = 22
    else:
        font_size = 48
        wrap_width = 26

    font = ImageFont.truetype(FONT_PATH, font_size)
    wrapped = textwrap.fill(text, width=wrap_width)

    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    position = ((WIDTH - text_w) / 2, (HEIGHT - text_h) / 2)

    _draw_text_with_shadow(
        draw, position, wrapped, font, fill=(255, 255, 255), align="center"
    )

    img.save(out_path, quality=95)


def _generate_tts(text: str, audio_path: str, preferred_lang: str = None) -> str:
    """TTS yaratadi, agar tanlangan til ishlamasa avtomatik boshqasiga o'tadi."""
    langs_to_try = []
    if preferred_lang:
        langs_to_try.append(preferred_lang)
    for lang in TTS_LANG_FALLBACK_ORDER:
        if lang not in langs_to_try:
            langs_to_try.append(lang)

    last_error = None
    for lang in langs_to_try:
        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(audio_path)
            return lang
        except Exception as e:
            last_error = e
            logger.warning(f"TTS til '{lang}' bilan ishlamadi: {e}")
            continue

    raise RuntimeError(f"Hech qanday til bilan ovoz yaratib bo'lmadi: {last_error}")


def create_simple_video(text: str, preferred_lang: str = None) -> str:
    """
    Matndan Reels formatidagi sifatli video yaratadi va yo'lini qaytaradi.
    Xatolik bo'lsa aniq, tushunarli xabar bilan Exception ko'taradi.
    """
    if not text or not text.strip():
        raise ValueError("Video uchun matn bo'sh bo'lishi mumkin emas")

    text = text.strip()
    session_id = str(uuid.uuid4())[:8]
    image_path = os.path.join(OUTPUT_DIR, f"{session_id}.png")
    audio_path = os.path.join(OUTPUT_DIR, f"{session_id}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"{session_id}.mp4")

    try:
        # 1. Fon rasmi
        _make_background_image(text, image_path)

        # 2. Ovoz (avtomatik fallback bilan)
        used_lang = _generate_tts(text, audio_path, preferred_lang)
        logger.info(f"TTS tili: {used_lang}")

        # 3. Audio davomiyligini aniqlaymiz (fade effektlar uchun)
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True, text=True, check=True,
        )
        duration = float(probe.stdout.strip())
        fade_duration = min(0.6, duration / 4)

        # 4. ffmpeg orqali video yig'ish (fade-in/out effektlari bilan)
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
            "-vf", f"fade=t=in:st=0:d={fade_duration},fade=t=out:st={duration - fade_duration}:d={fade_duration}",
            "-af", f"afade=t=in:st=0:d={fade_duration},afade=t=out:st={duration - fade_duration}:d={fade_duration}",
            "-shortest",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg xatolik berdi: {result.stderr[-500:]}")

        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise RuntimeError("Video fayli yaratilmadi (bo'sh natija)")

        return video_path

    finally:
        # Vaqtinchalik fayllarni tozalaymiz, faqat video qoladi
        for tmp in (image_path, audio_path):
            if os.path.exists(tmp):
                os.remove(tmp)
