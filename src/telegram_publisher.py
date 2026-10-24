#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Telegram Publisher (Every 6th Run / 3 Hours)
# Rules: 3 Approved Packages Only | Hard Safety Cap (<3500) | 4 Inline Buttons
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
DEFAULT_TARGET_CHAT = "@Goodbaye_filtering"
BASE_URL = "https://alireza786786.github.io/Free-V2ray-Configs"

# Maximum safe config count per file to prevent channel spam
MAX_SAFE_CONFIG_LIMIT = 3500

# 4 Official Inline Glass Buttons (Principle 2)
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

def build_caption(package_title: str, file_path: str, count: int) -> str:
    now_tehran = get_tehran_time()
    if jdatetime:
        j_now = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        date_str = j_now.strftime("%Y/%m/%d")
    else:
        date_str = now_tehran.strftime("%Y/%m/%d")

    time_str = now_tehran.strftime("%H:%M")

    return (
        f"🚀 *مجموعه کانفیگ‌های تست‌شده و زنده ({package_title})*\n"
        f"📡 مناسب دوران اختلال، فیلترینگ و شبکه ملی\n\n"
        f"📅 تاریخ شمسی: `{date_str}`\n"
        f"⏰ ساعت تهران: `{time_str}`\n"
        f"📊 شاخص کیفیت: `VIP Strict (Ping < 500ms)`\n"
        f"🔢 تعداد کانفیگ سالم این فایل: `{count}`\n\n"
        f"🌐 لینک مستقیم دانلود / سابسکریپشن:\n"
        f"`{BASE_URL}/{file_path}`"
    )

def main():
    bot_token = os.getenv("BOT_TOKEN")
    target_chat = os.getenv("TARGET_CHAT_ID", DEFAULT_TARGET_CHAT)

    if not bot_token:
        logger.info("BOT_TOKEN is not configured. Skipping Telegram broadcast.")
        return

    # Check 6th cycle counter (every 3 hours)
    Path("data").mkdir(exist_ok=True)
    count = 0
    if Path(COUNTER_FILE).exists():
        try:
            count = int(Path(COUNTER_FILE).read_text(encoding="utf-8").strip())
        except Exception:
            count = 0

    if count % 12 != 0:
        logger.info(f"⏳ Cycle #{count % 12}/12: Telegram broadcast deferred until cycle #12 (every 3 hours).")
        return

    logger.info(f"🚀 Cycle #{count}: Starting Telegram broadcast for 3 approved packages...")

    # The ONLY 3 Approved Packages
    APPROVED_PACKAGES = [
        ("all_servers.txt", "پکیج اصلی و جامع All VIP"),
        ("servers/lite.txt", "پکیج فوق‌سریع لایت Ultra"),
        ("servers/emergency_socks5.txt", "پروکسی‌های اضطراری SOCKS5")
    ]

    for file_path, title in APPROVED_PACKAGES:
        p = Path(file_path)
        if not p.exists():
            continue

        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

        total_lines = len(lines)
        if total_lines == 0:
            continue

        # Hard Safety Guard against 20k+ spam
        if total_lines > MAX_SAFE_CONFIG_LIMIT:
            logger.warning(f"🚨 Safety Alert: '{file_path}' has {total_lines} configs (exceeds {MAX_SAFE_CONFIG_LIMIT}). Blocked to protect channel.")
            continue

        caption = build_caption(title, file_path, total_lines)
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

        try:
            with open(p, "rb") as doc:
                files = {"document": (p.name, doc, "text/plain")}
                data = {
                    "chat_id": target_chat,
                    "caption": caption,
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps(INLINE_KEYBOARD)
                }
                resp = requests.post(url, data=data, files=files, timeout=35)
                if resp.status_code == 200:
                    logger.info(f"✅ Published '{title}' ({total_lines} configs) to {target_chat}")
                else:
                    logger.error(f"❌ Telegram API Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"❌ Network error sending {file_path}: {e}")

if __name__ == "__main__":
    main()
