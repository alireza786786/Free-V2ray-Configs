#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Telegram Subscription Publisher Engine
# Quality Policy: Ping < 500ms | 4 Official Inline Buttons | Jalali Caption
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests

try:
    import jdatetime
except ImportError:
    jdatetime = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("telegram_publisher")

# Destination Settings
DEFAULT_TARGET_CHAT = "@Goodbaye_filtering"
BASE_URL = "https://alireza786786.github.io/Free-V2ray-Configs"

# Telegram 4 Official Inline Keyboard Buttons (Principle 2)
INLINE_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "📢 کانال اصلی Goodbaye Filtering", "url": "https://t.me/Goodbaye_filtering"}
        ],
        [
            {"text": "⚡ کانال اختصاصی VIP", "url": "https://t.me/CONFIG_V2RAY_VIP"}
        ],
        [
            {"text": "🌐 وب‌پنل آنلاین سابسکریپشن", "url": f"{BASE_URL}/"}
        ],
        [
            {"text": "🔄 اشتراک‌گذاری با دوستان", "url": "https://t.me/share/url?url=https://t.me/Goodbaye_filtering"}
        ]
    ]
}

def get_tehran_time():
    """Calculates exact Tehran time (UTC+3:30)."""
    tz_tehran = timezone(timedelta(hours=3, minutes=30))
    now_utc = datetime.now(timezone.utc)
    return now_utc.astimezone(tz_tehran)

def get_jalali_date_str(now_tehran) -> str:
    """Returns official Jalali date format."""
    if jdatetime:
        j_now = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_now.strftime("%Y/%m/%d")
    else:
        # Fallback if library missing
        return now_tehran.strftime("%Y/%m/%d")

def build_caption(package_title: str, file_name: str, config_count: int) -> str:
    """
    Constructs the official Telegram caption according to Principle 3:
    🚀 مجموعه کانفیگ‌های تست‌شده و زنده ([عنوان پکیج])
    📡 مناسب دوران اختلال، فیلترینگ و شبکه ملی

    📅 تاریخ شمسی: `[تاریخ شمسی روز - جلالی]`
    ⏰ ساعت تهران: `[ساعت دقیق به افق تهران]`
    📊 شاخص کیفیت: `VIP Strict (Ping < 500ms)`
    🔢 تعداد کانفیگ سالم این فایل: `[تعداد خطوط واقعی داخل همان فایل]`

    🌐 لینک مستقیم دانلود / سابسکریپشن:
    https://alireza786786.github.io/Free-V2ray-Configs/[نام فایل]
    """
    now_tehran = get_tehran_time()
    jalali_date = get_jalali_date_str(now_tehran)
    time_str = now_tehran.strftime("%H:%M")

    caption = (
        f"🚀 *مجموعه کانفیگ‌های تست‌شده و زنده ({package_title})*\n"
        f"📡 مناسب دوران اختلال، فیلترینگ و شبکه ملی\n\n"
        f"📅 تاریخ شمسی: `{jalali_date}`\n"
        f"⏰ ساعت تهران: `{time_str}`\n"
        f"📊 شاخص کیفیت: `VIP Strict (Ping < 500ms)`\n"
        f"🔢 تعداد کانفیگ سالم این فایل: `{config_count}`\n\n"
        f"🌐 لینک مستقیم دانلود / سابسکریپشن:\n"
        f"`{BASE_URL}/{file_name}`"
    )
    return caption

def send_file_to_telegram(bot_token: str, chat_id: str, file_path: str, package_title: str) -> bool:
    path_obj = Path(file_path)
    if not path_obj.exists():
        logger.warning(f"File '{file_path}' does not exist. Skipping.")
        return False

    with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    config_count = len(lines)
    if config_count == 0:
        logger.warning(f"File '{file_path}' is empty. Skipping.")
        return False

    relative_name = path_obj.as_posix()
    caption = build_caption(package_title, relative_name, config_count)
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    try:
        with open(path_obj, "rb") as doc:
            files = {"document": (path_obj.name, doc, "text/plain")}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(INLINE_KEYBOARD)
            }
            resp = requests.post(url, data=data, files=files, timeout=30)
            if resp.status_code == 200:
                logger.info(f"✅ Successfully sent '{package_title}' ({config_count} configs) to {chat_id}")
                return True
            else:
                logger.error(f"❌ Telegram API Error ({resp.status_code}): {resp.text}")
                return False
    except Exception as e:
        logger.error(f"❌ Network error sending {file_path}: {e}")
        return False

def main():
    bot_token = os.getenv("BOT_TOKEN")
    target_chat = os.getenv("TARGET_CHAT_ID", DEFAULT_TARGET_CHAT)

    if not bot_token:
        logger.warning("BOT_TOKEN is not set in environment secrets. Skipping Telegram publishing.")
        return

    logger.info(f"📢 Publishing verified subscription packages to {target_chat}...")

    # Packages to publish with respective official titles
    packages = [
        ("all_servers.txt", "پکیج اصلی و جامع All VIP"),
        ("servers/lite.txt", "پکیج فوق‌سریع لایت Ultra"),
        ("servers/no_cloudflare.txt", "پکیج اختصاصی بدون کلودفلر"),
        ("servers/emergency_socks5.txt", "پروکسی‌های اضطراری SOCKS5")
    ]

    success_count = 0
    for file_path, title in packages:
        if send_file_to_telegram(bot_token, target_chat, file_path, title):
            success_count += 1

    logger.info(f"🏁 Published {success_count} subscription files to Telegram successfully.")

if __name__ == "__main__":
    main()
