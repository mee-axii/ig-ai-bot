"""
Instagram Graph API bilan ishlash.

Kerakli narsalar (Meta for Developers'da bepul olinadi):
  - IG_BUSINESS_ACCOUNT_ID  -> Instagram Business/Creator akkaunt ID
  - IG_ACCESS_TOKEN         -> Uzoq muddatli (long-lived) Access Token
  - Video internetdan ochiq URL orqali yuklanishi kerak (Graph API talabi),
    shuning uchun avval videoni biror bepul joyga (masalan GitHub yoki
    Cloudinary bepul tarifi) yuklab, ochiq havolasini olamiz.
"""

import os
import time
import requests

GRAPH_API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")


def _check_config():
    if not IG_BUSINESS_ACCOUNT_ID or not IG_ACCESS_TOKEN:
        raise RuntimeError(
            "IG_BUSINESS_ACCOUNT_ID yoki IG_ACCESS_TOKEN sozlanmagan. "
            "Render Environment bo'limiga qo'shing."
        )


def get_account_stats() -> dict:
    """Akkaunt haqida asosiy statistikani qaytaradi."""
    _check_config()

    url = f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}"
    params = {
        "fields": "followers_count,media_count",
        "access_token": IG_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Oxirgi postning reach (ta'sir doirasi) ko'rsatkichini olishga urinamiz
    last_reach = None
    try:
        media_url = f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}/media"
        media_resp = requests.get(
            media_url,
            params={"fields": "id", "limit": 1, "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        media_resp.raise_for_status()
        items = media_resp.json().get("data", [])
        if items:
            media_id = items[0]["id"]
            insights_url = f"{BASE_URL}/{media_id}/insights"
            insights_resp = requests.get(
                insights_url,
                params={"metric": "reach", "access_token": IG_ACCESS_TOKEN},
                timeout=30,
            )
            if insights_resp.ok:
                insights_data = insights_resp.json().get("data", [])
                if insights_data:
                    last_reach = insights_data[0]["values"][0]["value"]
    except Exception:
        pass  # statistika bo'lmasa ham asosiy ma'lumot ko'rsatiladi

    data["last_reach"] = last_reach
    return data


def post_video_to_instagram(video_public_url: str, caption: str = "") -> str:
    """
    video_public_url  - internetda ochiq turgan video havolasi (Reels sifatida joylanadi)
    Qaytaradi: joylangan post ID.

    ESLATMA: Instagram Graph API videoni faqat ochiq URL orqali qabul qiladi,
    telefondagi faylni to'g'ridan-to'g'ri yubora olmaymiz. Shuning uchun
    video avval biror bepul fayl-xosting joyga (masalan GitHub raw link
    yoki Cloudinary) yuklanishi kerak - bot.py buni video.py bilan birga
    avtomatik bajaradi (upload_video_and_get_url funksiyasi orqali).
    """
    _check_config()

    # 1-qadam: media konteyner yaratish
    create_url = f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}/media"
    create_params = {
        "media_type": "REELS",
        "video_url": video_public_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    }
    create_resp = requests.post(create_url, params=create_params, timeout=60)
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # 2-qadam: video qayta ishlanishini kutish
    status_url = f"{BASE_URL}/{creation_id}"
    for _ in range(30):  # taxminan 5 daqiqagacha kutadi
        status_resp = requests.get(
            status_url,
            params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
            timeout=30,
        )
        status_resp.raise_for_status()
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        time.sleep(10)
    else:
        raise TimeoutError("Video qayta ishlash vaqti tugadi (5 daqiqa)")

    # 3-qadam: joylash (publish)
    publish_url = f"{BASE_URL}/{IG_BUSINESS_ACCOUNT_ID}/media_publish"
    publish_params = {"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN}
    publish_resp = requests.post(publish_url, params=publish_params, timeout=60)
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]
