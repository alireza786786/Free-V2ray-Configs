#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Telegram Channel Config Collector (No-API)
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import requests
import re
import sqlite3
import time
import logging
import json
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----- تنظیمات -----
CHANNELS_FILE = "data/channels.txt"       # فایل ورودی کانال‌ها
DB_FILE = "collector.db"                  # پایگاه‌داده مشترک
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SLEEP_BETWEEN_CHANNELS = 1.2             # تاخیر استاندارد بین واکشی‌ها

# ----- الگوی استخراج جامع پروتکل‌ها -----
V2RAY_PATTERN = re.compile(
    r'(?:vless|vmess|trojan|ss|ssr|hysteria|hysteria2|tuic|juicity|socks[45]?)://[^\s`\'"<>]+',
    flags=re.IGNORECASE
)

def load_channels(filepath: str) -> list[str]:
    """بارگذاری لیست کانال‌ها از فایل."""
    path = Path(filepath)
    if not path.exists():
        logger.error(f"فایل '{filepath}' پیدا نشد.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        channels = [line.strip().lstrip('@') for line in f if line.strip() and not line.startswith('#')]
    logger.info(f"تعداد {len(channels)} کانال از '{filepath}' بارگذاری شد.")
    return channels

def fetch_page(channel: str) -> str:
    """دریافت محتوای وب‌پیش‌نمایش کانال t.me/s."""
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"خطا در واکشی {channel}: {e}")
        return ""

def extract_configs(html: str) -> set[str]:
    """استخراج کلیه لینک‌های معتبر از محتوای HTML."""
    return set(V2RAY_PATTERN.findall(html))

def save_to_db(configs: set[str]):
    """ذخیره امن کانفیگ‌های یکتا در SQLite."""
    conn = sqlite3.connect(DB_FILE)
    try:
        with conn:
            conn.executemany(
                "INSERT OR IGNORE INTO configs (config) VALUES (?)",
                [(c,) for c in configs]
            )
        logger.info(f"{len(configs)} کانفیگ جدید به دیتابیس اضافه شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره‌سازی دیتابیس: {e}")
    finally:
        conn.close()

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("CREATE TABLE IF NOT EXISTS configs (config TEXT PRIMARY KEY)")
    conn.close()

    logger.info("🚀 شروع جمع‌آوری کانفیگ‌ها از تلگرام...")
    channels = load_channels(CHANNELS_FILE)
    if not channels:
        return

    last_ids_file = "data/last_message_id.json"
    last_ids = {}
    if Path(last_ids_file).exists():
        try:
            with open(last_ids_file, "r", encoding="utf-8") as f:
                last_ids = json.load(f)
        except Exception:
            pass

    channel_results = []
    all_configs = set()
    invalid_channels = []

    for idx, ch in enumerate(channels, 1):
        logger.info(f"📡 [{idx}/{len(channels)}] واکشی کانال: {ch}")
        html = fetch_page(ch)
        if not html:
            channel_results.append((ch, 0))
            if idx < len(channels):
                time.sleep(SLEEP_BETWEEN_CHANNELS)
            continue

        msg_pattern = re.compile(r'data-post="[^"]+/(\d+)"')
        msg_ids = [int(m) for m in msg_pattern.findall(html)]

        if not msg_ids:
            logger.warning("   ↳ هیچ شناسه پیامی یافت نشد (احتمالاً کانال خصوصی، مسدود یا حذف شده)")
            invalid_channels.append(ch)
            channel_results.append((ch, "ERR"))
            if idx < len(channels):
                time.sleep(SLEEP_BETWEEN_CHANNELS)
            continue

        last_id = last_ids.get(ch, 0)
        new_msg_ids = [m for m in msg_ids if m > last_id]

        if new_msg_ids:
            found = extract_configs(html)
            logger.info(f"   ↳ {len(found)} کانفیگ استخراج شد (پیام‌های تازه: {len(new_msg_ids)})")
            all_configs.update(found)
            channel_results.append((ch, len(found)))
            last_ids[ch] = max(msg_ids)
        else:
            logger.info(f"   ↳ ۰ پیام جدید — تمامی {len(msg_ids)} پست قبلاً خوانده شده‌اند")
            channel_results.append((ch, 0))

        if idx < len(channels):
            time.sleep(SLEEP_BETWEEN_CHANNELS)

    # بروزرسانی شناسه‌های پیام‌ها
    try:
        Path("data").mkdir(exist_ok=True)
        with open(last_ids_file, "w", encoding="utf-8") as f:
            json.dump(last_ids, f, indent=2)
    except Exception as e:
        logger.warning(f"خطا در ذخیره last_message_id.json: {e}")

    # تفکیک کانال‌های نامعتبر
    if invalid_channels:
        invalid_file = "data/invalid_channels.txt"
        try:
            with open(invalid_file, "w", encoding="utf-8") as f:
                f.write(f"Invalid Telegram Channels — {datetime.now(timezone.utc).isoformat()}\n\n")
                for ch in invalid_channels:
                    f.write(f"{ch}\n")
        except Exception as e:
            logger.warning(f"خطا در ذخیره invalid_channels.txt: {e}")

    if all_configs:
        save_to_db(all_configs)
    else:
        logger.warning("در این اجرا کانفیگ جدیدی یافت نشد.")

    # بروزرسانی فایل گزارش عملکرد کانال‌ها
    report_file = "data/channel_report.txt"
    history = {}
    if Path(report_file).exists():
        with open(report_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                c_name, counts = parts
                c_name = c_name.strip()
                counts_clean = [c.strip() for c in counts.split(',') if c.strip().isdigit() or c.strip() == "ERR"]
                history[c_name] = counts_clean

    for ch, count in channel_results:
        val = str(count)
        if ch in history:
            history[ch].append(val)
        else:
            history[ch] = [val]

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Telegram Channel Report — last update: {datetime.now(timezone.utc).isoformat()}\n\n")
        for ch in sorted(history.keys()):
            counts_str = ", ".join(history[ch])
            f.write(f"{ch}: {counts_str}\n")

    logger.info("✅ پایان موفقیت‌آمیز جمع‌آوری تلگرام.")

if __name__ == "__main__":
    main()
