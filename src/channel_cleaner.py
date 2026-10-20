#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Telegram Channel Health Checker & Cleaner
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import time
from pathlib import Path
import requests

INPUT_FILE = "data/channels.txt"
VALID_FILE = "data/channels_cleaned.txt"
INVALID_FILE = "data/invalid_channels.txt"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
TIMEOUT = 8

def main():
    if not Path(INPUT_FILE).exists():
        print(f"❌ '{INPUT_FILE}' not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        channels = [line.strip().lstrip('@') for line in f if line.strip() and not line.startswith('#')]

    print(f"🔍 Checking health for {len(channels)} Telegram channels...")
    valid = []
    invalid = []

    os.makedirs("data", exist_ok=True)

    for i, ch in enumerate(channels, 1):
        url = f"https://t.me/s/{ch}"
        try:
            r = requests.head(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                valid.append(ch)
            else:
                invalid.append(f"{ch} # HTTP {r.status_code}")
        except Exception as e:
            invalid.append(f"{ch} # {type(e).__name__}")

        if i % 25 == 0 or i == len(channels):
            print(f"   ↳ [{i}/{len(channels)}] checked... (Active: {len(valid)}, Invalid: {len(invalid)})")
        
        time.sleep(0.15)  # Safe delay to prevent Telegram rate-limiting

    Path(VALID_FILE).write_text("\n".join(valid) + "\n", encoding="utf-8")
    Path(INVALID_FILE).write_text("\n".join(invalid) + "\n", encoding="utf-8")
    print(f"✅ Channel cleaning done! Valid: {len(valid)} saved to '{VALID_FILE}', Invalid: {len(invalid)}")

if __name__ == "__main__":
    main()
