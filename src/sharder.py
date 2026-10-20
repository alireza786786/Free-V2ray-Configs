#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Subscription Sharding & Package Generator
# Quality Policy: Ping < 500ms | Lite, No-Cloudflare, Countries, SOCKS5
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("sharder")

INPUT_TESTED_JSON = "data/tested_servers.json"
SERVERS_DIR = "servers"
COUNTRIES_DIR = "servers/countries"
STATS_FILE = "data/sub_stats.json"

CLOUDFLARE_KEYWORDS = ["cloudflare", "cf-", "warp", "workers.dev", "pages.dev"]

def sanitize_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")

def is_cloudflare(item: dict) -> bool:
    dc = item.get("datacenter", "").lower()
    city = item.get("city", "").lower()
    raw = item.get("raw_uri", "").lower()
    return any(k in dc or k in city or k in raw for k in CLOUDFLARE_KEYWORDS)

def main():
    if not Path(INPUT_TESTED_JSON).exists():
        logger.error(f"Tested file '{INPUT_TESTED_JSON}' not found. Run remarker first.")
        return

    with open(INPUT_TESTED_JSON, "r", encoding="utf-8") as f:
        try:
            servers = json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON: {e}")
            return

    if not servers:
        logger.warning("No tested servers available to shard.")
        return

    # Create output directories
    os.makedirs(SERVERS_DIR, exist_ok=True)
    os.makedirs(COUNTRIES_DIR, exist_ok=True)

    # Initialize collections
    proto_groups: dict[str, list[str]] = {}
    country_groups: dict[str, list[str]] = {}
    lite_list: list[str] = []
    no_cf_list: list[str] = []
    emergency_socks: list[str] = []
    iran_ping_list: list[str] = []

    # Filter servers (Sort strictly by latency)
    sorted_servers = sorted(servers, key=lambda x: x.get("ping", 999))

    for item in sorted_servers:
        raw_uri = item.get("raw_uri", "").strip()
        scheme = item.get("scheme", "other").lower()
        cc = item.get("country_code", "GL").upper()
        country_name = item.get("country", "Global")
        ping = item.get("ping", 500)

        # 1. Protocol Grouping
        proto_groups.setdefault(scheme, []).append(raw_uri)

        # 2. Country Grouping
        country_slug = sanitize_filename(country_name)
        country_groups.setdefault(country_slug, []).append(raw_uri)

        # 3. Lite Package (Top 70 fastest servers under 380ms)
        if len(lite_list) < 70 and ping <= 380:
            lite_list.append(raw_uri)

        # 4. No-Cloudflare Package
        if not is_cloudflare(item):
            no_cf_list.append(raw_uri)

        # 5. Emergency SOCKS5
        if scheme in ("socks", "socks4", "socks5"):
            emergency_socks.append(raw_uri)

        # 6. Ultra-Low Ping (Iran-friendly ping < 280ms)
        if ping <= 280:
            iran_ping_list.append(raw_uri)

    # Write Protocol files
    for proto, configs in proto_groups.items():
        fname = f"{SERVERS_DIR}/{proto}.txt"
        Path(fname).write_text("\n".join(configs) + "\n", encoding="utf-8")
        logger.info(f"   ↳ Sharded {proto.upper()}: {len(configs)} configs -> {fname}")

    # Write Country files
    for c_slug, configs in country_groups.items():
        fname = f"{COUNTRIES_DIR}/{c_slug}.txt"
        Path(fname).write_text("\n".join(configs) + "\n", encoding="utf-8")

    # Write Curated Packages
    Path(f"{SERVERS_DIR}/lite.txt").write_text("\n".join(lite_list) + "\n", encoding="utf-8")
    Path(f"{SERVERS_DIR}/no_cloudflare.txt").write_text("\n".join(no_cf_list) + "\n", encoding="utf-8")
    Path(f"{SERVERS_DIR}/emergency_socks5.txt").write_text("\n".join(emergency_socks) + "\n", encoding="utf-8")
    Path(f"{SERVERS_DIR}/iran_fast.txt").write_text("\n".join(iran_ping_list) + "\n", encoding="utf-8")

    # Build statistics for Web Panel
    stats = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_active": len(servers),
        "lite_count": len(lite_list),
        "no_cf_count": len(no_cf_list),
        "emergency_count": len(emergency_socks),
        "iran_fast_count": len(iran_ping_list),
        "protocols": {p: len(cfgs) for p, cfgs in proto_groups.items()},
        "top_countries": {c: len(cfgs) for c, cfgs in list(country_groups.items())[:10]}
    }

    Path(STATS_FILE).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"✅ Sharding complete. Stats saved to '{STATS_FILE}'")

if __name__ == "__main__":
    main()
