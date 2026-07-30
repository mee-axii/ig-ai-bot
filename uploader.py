"""
Instagram Graph API videoni faqat ochiq (public) URL orqali qabul qiladi.
Shuning uchun avval videoni bepul Cloudinary xizmatiga yuklab, ochiq
havolasini olamiz.

Cloudinary bepul tarifi: https://cloudinary.com (ro'yxatdan o'tish bepul,
kredit karta talab qilinmaydi, oyiga 25 kredit bepul beriladi - bir necha
yuzlab qisqa videolar uchun yetarli).

Kerakli environment o'zgaruvchilari:
  CLOUDINARY_CLOUD_NAME
  CLOUDINARY_API_KEY
  CLOUDINARY_API_SECRET
"""

import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_video_and_get_url(local_path: str) -> str:
    """Videoni Cloudinary'ga yuklaydi va ochiq URL manzilini qaytaradi."""
    result = cloudinary.uploader.upload(
        local_path,
        resource_type="video",
        folder="ig_ai_bot",
    )
    return result["secure_url"]
