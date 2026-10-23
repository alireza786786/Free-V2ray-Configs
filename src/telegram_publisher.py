#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Telegram Publisher (Every 6th Run / 3 Hours)
# Broadcasts ONLY all_servers.txt with 4 Glass Buttons & Jalali Caption
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("telegram_publisher")

COUNTER_FILE = "data/publish_counter.txt"
ALL_SERVERS = "all_servers.txt"
DEFAULT_TARGET_CHAT = "@Goodbaye_filtering"
BASE_URL = "https://alireza786786.github.io/Free-V2ray-Configs"

INLINE_KEYBOARD = {
    "inline_keyboard": [
        [{"text": "📢 کانال اصلی Goodbaye Filtering", "url": "https://t.me/Goodbaye_filtering"}],
        [{"text": "⚡ کانال اختصاصی VIP", "url": "https://t.me/CONFIG_V2RAY_VIP"}],
        [{"text": "🌐 وب‌پنل آنلاین سابسکریپشن", "url": f"{BASE_URL}/"}],
        [{"text": "🔄 اشتراک‌گذاری با دوستان", "url": "https://t.me/share/url?url=https://t.me/Goodbaye_filtering"}]
    ]
}

def get_tehran_time():
    tz_tehran = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(timezone.utc).astimezone(tz_tehran)

def build_caption(config_count: int) -> str:
    now_tehran = get_tehran_time()
    if jdatetime:
        j_now = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        date_str = j_now.strftime("%Y/%m/%d")
    else:
        date_str = now_tehran.strftime("%Y/%m/%d")

    time_str = now_tehran.strftime("%H:%M")

    return (
        f"🚀 *مجموعه کانفیگ‌های تست‌شده و زنده (پکیج اصلی و جامع All VIP)*\n"
        f"📡 مناسب دوران اختلال، فیلترینگ و شبکه ملی\n\n"
        f"📅 تاریخ شمسی: `{date_str}`\n"
        f"⏰ ساعت تهران: `{time_str}`\n"
        f"📊 شاخص کیفیت: `VIP Strict (Ping < 500ms)`\n"
        f"🔢 تعداد کانفیگ سالم این فایل: `{config_count}`\n\n"
        f"🌐 لینک مستقیم دانلود / سابسکریپشن:\n"
        f"`{BASE_URL}/all_servers.txt`"
    )

def main():
    bot_token = os.getenv("BOT_TOKEN")
    target_chat = os.getenv("TARGET_CHAT_ID", DEFAULT_TARGET_CHAT)

    if not bot_token:
        logger.info("BOT_TOKEN is not set. Skipping Telegram publisher.")
        return

    # --- مدیریت شمارنده ارسال دور ششم (هر ۳ ساعت) ---
    Path("data").mkdir(exist_ok=True)
    count = 0
    if Path(COUNTER_FILE).exists():
        try:
            count = int(Path(COUNTER_FILE).read_text(encoding="utf-8").strip())
        except Exception:
            count = 0

    count += 1
    Path(COUNTER_FILE).write_text(str(count), encoding="utf-8")

    logger.info(f"Current Execution Cycle: #{count} / 6")

    # اگر هنوز دور ششم نرسیده است، پیام ارسال نمی‌شود
    if count % 6 != 0:
        logger.info(f"⏳ Cycle #{count}: Skipping broadcast. Will broadcast on cycle #6 (every 3 hours).")
        return

    logger.info("🚀 6th Cycle Reached! Broadcasting 'all_servers.txt' to Telegram...")

    if not Path(ALL_SERVERS).exists():
        logger.warning(f"{ALL_SERVERS} not found.")
        return

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    if not lines:
        logger.warning(f"{ALL_SERVERS} is empty.")
        return

    caption = build_caption(len(lines))
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

    try:
        with open(ALL_SERVERS, "rb") as doc:
            files = {"document": ("all_servers.txt", doc, "text/plain")}
            data = {
                "chat_id": target_chat,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(INLINE_KEYBOARD)
            }
            resp = requests.post(url, data=data, files=files, timeout=30)
            if resp.status_code == 200:
                logger.info(f"✅ Successfully published all_servers.txt ({len(lines)} configs) to {target_chat}")
            else:
                logger.error(f"❌ Telegram API Error ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"❌ Error sending document: {e}")

if __name__ == "__main__":
    main()
