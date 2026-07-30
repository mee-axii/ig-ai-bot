"""
Instagram Graph API videoni faqat ochiq (public) URL orqali qabul qiladi.
Bu versiyada tashqi xizmat (Cloudinary va h.k.) kerak emas - video
to'g'ridan-to'g'ri shu bot ishlab turgan Render serveridan beriladi.

bot.py ichidagi kichik HTTP server "/video/<fayl_nomi>" manzili orqali
video faylni taqdim etadi, biz shunchaki to'liq (public) havolani
yasab beramiz.

Render avtomatik ravishda RENDER_EXTERNAL_URL degan environment
o'zgaruvchisini o'zi qo'yadi (masalan https://ig-ai-bot.onrender.com) -
buni qo'lda kiritish shart emas.
"""

import os


def get_public_video_url(local_path: str) -> str:
    base_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("PUBLIC_BASE_URL")
    if not base_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL topilmadi. Agar Render'dan boshqa joyda "
            "ishlatsangiz, PUBLIC_BASE_URL environment o'zgaruvchisini "
            "qo'lda kiriting (masalan https://sizning-manzil.com)."
        )
    base_url = base_url.rstrip("/")
    filename = os.path.basename(local_path)
    return f"{base_url}/video/{filename}"
