#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Autonomous Source Discovery Engine
# Capabilities: Dynamic GitHub Repo Hunting & Auto Telegram Channel Discovery
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import re
import sys
import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
import aiohttp
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("source_discovery")

# Configuration
DISCOVERED_REPOS_FILE = "data/discovered_repos.txt"
DISCOVERED_CHANNELS_FILE = "data/discovered_channels.txt"
EXISTING_CHANNELS_FILE = "data/channels.txt"
INVALID_CHANNELS_FILE = "data/invalid_channels.txt"

SEARCH_QUERIES = [
    "v2ray config", "vless reality", "clash meta subscription",
    "hysteria2 subscription", "sing-box configs", "فیلترشکن رایگان",
    "کانفیگ v2ray", "free vpn node"
]

TG_LINK_PATTERN = re.compile(
    r'(?:https?://t\.me/(?:s/)?|@)([a-zA-Z0-9_]{5,32})',
    re.IGNORECASE
)

IGNORED_TG_KEYWORDS = {
    "bot", "joinchat", "share", "addstickers", "proxy", "socks5",
    "telegram", "username", "channel", "contact", "login", "signup"
}

def get_github_token() -> str:
    load_dotenv("config/.env")
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    return token or ""

def load_existing_set(file_path: str) -> set[str]:
    path = Path(file_path)
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return {line.strip().lstrip('@').lower() for line in f if line.strip() and not line.startswith('#')}

# ==============================================================================
# 1. GitHub Repo Discovery
# ==============================================================================
async def search_github_new_repos(session: aiohttp.ClientSession, headers: dict) -> set[tuple[str, str]]:
    discovered = set()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    logger.info(f"🔎 Hunting new GitHub repositories pushed since {cutoff_date}...")

    for query in SEARCH_QUERIES:
        full_query = f"{query} pushed:>{cutoff_date}"
        params = {"q": full_query, "sort": "updated", "order": "desc", "per_page": 50}
        try:
            async with session.get("https://api.github.com/search/repositories", headers=headers, params=params, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    for item in items:
                        full_name = item.get("full_name", "")
                        if "/" in full_name:
                            owner, repo = full_name.split("/", 1)
                            discovered.add((owner.strip(), repo.strip()))
                elif resp.status in (403, 429):
                    logger.warning("GitHub Search rate-limit reached. Pausing search.")
                    break
        except Exception as e:
            logger.debug(f"Search query error '{query}': {e}")
        await asyncio.sleep(1.5)

    logger.info(f"🎯 Total new repository candidates found: {len(discovered)}")
    return discovered

# ==============================================================================
# 2. Telegram Channel Discovery & Health Check
# ==============================================================================
async def verify_telegram_channel(session: aiohttp.ClientSession, username: str) -> bool:
    """Verifies if the public channel actually exists and has content via t.me/s/."""
    url = f"https://t.me/s/{username}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
    try:
        async with session.get(url, headers=headers, timeout=8) as resp:
            if resp.status == 200:
                html = await resp.text()
                # Must contain post identifiers
                if 'data-post="' in html:
                    return True
    except Exception:
        pass
    return False

async def extract_tg_from_github_repo(session: aiohttp.ClientSession, owner: str, repo: str) -> set[str]:
    """Scrapes README files of GitHub repos to harvest advertised Telegram channels."""
    found_channels = set()
    readme_urls = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
    ]
    for url in readme_urls:
        try:
            async with session.get(url, timeout=6) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    matches = TG_LINK_PATTERN.findall(content)
                    for m in matches:
                        clean = m.lower().strip()
                        if clean not in IGNORED_TG_KEYWORDS and not clean.endswith("bot") and len(clean) >= 5:
                            found_channels.add(clean)
                    if found_channels:
                        break
        except Exception:
            continue
    return found_channels

# ==============================================================================
# Main Runner
# ==============================================================================
async def main():
    logger.info("🚀 Starting Source Discovery Engine...")
    Path("data").mkdir(exist_ok=True)

    token = get_github_token()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SourceDiscovery/1.0"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    existing_channels = load_existing_set(EXISTING_CHANNELS_FILE)
    invalid_channels = load_existing_set(INVALID_CHANNELS_FILE)
    known_channels = existing_channels | invalid_channels

    async with aiohttp.ClientSession() as session:
        # Step 1: Discover Repos
        new_repos = await search_github_new_repos(session, headers)

        # Save Discovered Repos
        if new_repos:
            existing_repos_text = ""
            if Path(DISCOVERED_REPOS_FILE).exists():
                existing_repos_text = Path(DISCOVERED_REPOS_FILE).read_text(encoding="utf-8")
            
            with open(DISCOVERED_REPOS_FILE, "a", encoding="utf-8") as f:
                for o, r in sorted(new_repos):
                    entry = f'("{o}", "{r}")'
                    if entry not in existing_repos_text:
                        f.write(f"{entry}\n")
            logger.info(f"💾 Saved candidate repositories to '{DISCOVERED_REPOS_FILE}'")

        # Step 2: Harvest Telegram Channels from discovered Repos
        logger.info("📡 Scanning repo documentations for candidate Telegram channels...")
        candidate_tg = set()
        for o, r in list(new_repos)[:60]:  # Limit deep scans to preserve speed
            tg_handles = await extract_tg_from_github_repo(session, o, r)
            for h in tg_handles:
                if h not in known_channels:
                    candidate_tg.add(h)

        logger.info(f"🔎 Testing {len(candidate_tg)} new Telegram channel candidates...")
        verified_new_channels = []

        for ch in candidate_tg:
            is_valid = await verify_telegram_channel(session, ch)
            if is_valid:
                logger.info(f"   ✨ Verified new active channel: @{ch}")
                verified_new_channels.append(ch)
            await asyncio.sleep(0.3)

        # Save Discovered Channels
        if verified_new_channels:
            with open(DISCOVERED_CHANNELS_FILE, "a", encoding="utf-8") as f:
                for ch in sorted(verified_new_channels):
                    f.write(f"{ch}\n")
            logger.info(f"✅ Successfully discovered {len(verified_new_channels)} new active channels in '{DISCOVERED_CHANNELS_FILE}'")
        else:
            logger.info("No new unique Telegram channels discovered this run.")

    logger.info("🏁 Source Discovery completed successfully.")

if __name__ == "__main__":
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    asyncio.run(main())
