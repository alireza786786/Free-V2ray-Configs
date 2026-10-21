#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - High-Speed Latency & GeoIP Probe Engine
# Quality Policy: VIP Strict (Ping < 500ms) | Zero-Cost Public GeoIP
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

from __future__ import annotations

import os
import sys
import json
import time
import socket
import asyncio
import base64
import logging
from typing import Optional, Tuple, Dict, List, Any
from urllib.parse import urlsplit, parse_qsl, unquote
from pathlib import Path
import aiohttp
from tqdm import tqdm

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("checker")

# Quality strict threshold: ONLY servers with ping < 500ms pass
MAX_PING_THRESHOLD_MS = 500
PROBE_TIMEOUT_SECONDS = 0.500
MAX_CONCURRENT_PROBES = 120
GEO_CACHE_FILE = "data/geoip_cache.json"
OUTPUT_TESTED_JSON = "data/tested_servers.json"

# Persian translations for common VPN countries
FA_COUNTRY_MAP = {
    "DE": "آلمان", "NL": "هلند", "US": "آمریکا", "GB": "انگلیس",
    "FR": "فرانسه", "TR": "ترکیه", "FI": "فنلاند", "SE": "سوئد",
    "CH": "سوئیس", "CA": "کانادا", "SG": "سنگاپور", "JP": "ژاپن",
    "AE": "امارات", "IT": "ایتالیا", "ES": "اسپانیا", "PL": "لهستان",
    "AT": "اتریش", "NO": "نروژ", "DK": "دانمارک", "BE": "بلژیک",
    "RU": "روسیه", "IR": "ایران", "UA": "اوکراین", "RO": "رومانی",
    "CZ": "جمهوری چک", "AU": "استرالیا", "IN": "هند", "KR": "کره جنوبی",
    "HK": "هنگ کنگ", "TW": "تایوان", "BR": "برزیل", "ZA": "آفریقای جنوبی",
    "BG": "بلغارستان", "HU": "مجارستان", "IE": "ایرلند", "PT": "پرتغال"
}

def country_code_to_flag(code: str) -> str:
    """Dynamically converts any 2-letter ISO country code to its Unicode Flag Emoji."""
    if not code or len(code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c.upper())) for c in code)

def safe_b64_decode(text: str) -> str:
    s = text.strip()
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def parse_proxy_endpoint(uri: str) -> tuple[str, Optional[str], Optional[int]]:
    """
    Extracts protocol, host, and port from all supported proxy URI schemes.
    """
    line = uri.strip()
    if "://" not in line:
        return "", None, None

    scheme, rest = line.split("://", 1)
    scheme = scheme.lower()

    if scheme == "vmess":
        payload = rest.split("#", 1)[0].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                host = str(data.get("add", "")).strip()
                port = int(data.get("port", 0))
                return scheme, host, port
            except Exception:
                pass
        return scheme, None, None

    if scheme == "ss":
        part = rest.split("#", 1)[0].split("?", 1)[0]
        if "@" in part:
            _, host_port = part.rsplit("@", 1)
        else:
            decoded = safe_b64_decode(part)
            if "@" in decoded:
                _, host_port = decoded.rsplit("@", 1)
            else:
                host_port = decoded

        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            host = host.strip("[]").strip()
            if port_str.isdigit():
                return scheme, host, int(port_str)
        return scheme, None, None

    # VLESS, Trojan, Hysteria, Hysteria2, TUIC, Juicity, SOCKS4/5
    try:
        parsed = urlsplit(line)
        host = parsed.hostname
        port = parsed.port
        if host and port:
            return scheme, host, int(port)
    except Exception:
        pass

    return scheme, None, None

async def measure_tcp_handshake(host: str, port: int, timeout: float = PROBE_TIMEOUT_SECONDS) -> Optional[int]:
    """
    Measures the exact TCP connection latency in milliseconds.
    Strictly times out at 500ms to guarantee high responsiveness.
    """
    start_time = time.perf_counter()
    try:
        coro = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(coro, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        latency = (time.perf_counter() - start_time) * 1000.0
        int_latency = int(latency)
        return int_latency if int_latency < MAX_PING_THRESHOLD_MS else None
    except Exception:
        return None

class FreeGeoResolver:
    """100% Free Batch GeoIP Resolver using public zero-cost endpoints with persistent cache."""
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache: dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self):
        if Path(self.cache_file).exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save_cache(self):
        try:
            Path("data").mkdir(exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save GeoIP cache: {e}")

    async def resolve_ips(self, ips: list[str]) -> dict[str, dict]:
        results = {}
        unresolved = []

        for ip in ips:
            if ip in self.cache:
                results[ip] = self.cache[ip]
            else:
                unresolved.append(ip)

        if not unresolved:
            return results

        # Process in free batch queries of 100 IPs
        batch_size = 100
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            for i in range(0, len(unresolved), batch_size):
                chunk = unresolved[i:i + batch_size]
                try:
                    url = "http://ip-api.com/batch?fields=status,country,countryCode,city,org,as,query"
                    async with session.post(url, json=chunk) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for item in data:
                                q_ip = item.get("query")
                                if item.get("status") == "success":
                                    cc = item.get("countryCode", "UN")
                                    country_name = item.get("country", "Unknown")
                                    country_fa = FA_COUNTRY_MAP.get(cc, country_name)
                                    flag = country_code_to_flag(cc)
                                    city = item.get("city", "") or "Datacenter"
                                    raw_org = item.get("org", "") or item.get("as", "")
                                    datacenter = self._clean_datacenter(raw_org)

                                    geo_info = {
                                        "country": country_name,
                                        "country_fa": country_fa,
                                        "country_code": cc,
                                        "flag": flag,
                                        "city": city,
                                        "datacenter": datacenter
                                    }
                                    self.cache[q_ip] = geo_info
                                    results[q_ip] = geo_info
                        elif resp.status == 429:
                            await asyncio.sleep(2)
                except Exception as e:
                    logger.debug(f"Free GeoIP Batch error: {e}")

        # Fallback for any remaining unresolvable IPs
        for ip in unresolved:
            if ip not in results:
                fallback = {
                    "country": "Global",
                    "country_fa": "اینترنت آزاد",
                    "country_code": "GL",
                    "flag": "🌐",
                    "city": "Global",
                    "datacenter": "Cloud Gateway"
                }
                self.cache[ip] = fallback
                results[ip] = fallback

        self.save_cache()
        return results

    @staticmethod
    def _clean_datacenter(raw_org: str) -> str:
        """Cleans ASN and organization names into concise, readable datacenter tags."""
        if not raw_org:
            return "Dedicated Server"
        org = raw_org.split(" ", 1)[-1] if raw_org.startswith("AS") and " " in raw_org else raw_org
        cleaned = org.split(",")[0].replace("LLC", "").replace("Inc.", "").replace("GmbH", "").strip()
        for known in ["Cloudflare", "Hetzner", "OVH", "DigitalOcean", "Amazon", "Google", "Oracle", "Linode", "Contabo", "M247"]:
            if known.lower() in cleaned.lower():
                return known
        return cleaned[:22] if cleaned else "Fast Datacenter"

async def check_single_config(uri: str, semaphore: asyncio.Semaphore) -> Optional[dict]:
    scheme, host, port = parse_proxy_endpoint(uri)
    if not host or not port:
        return None

    # Resolve IP (non-blocking)
    try:
        resolved_ip = await asyncio.get_event_loop().run_in_executor(
            None, socket.gethostbyname, host
        )
    except Exception:
        return None

    ip_version = "IPv6" if ":" in resolved_ip else "IPv4"

    async with semaphore:
        latency = await measure_tcp_handshake(resolved_ip, port)
        if latency is None or latency >= MAX_PING_THRESHOLD_MS:
            return None

    return {
        "raw_uri": uri,
        "scheme": scheme,
        "host": host,
        "ip": resolved_ip,
        "port": port,
        "ping": latency,
        "ip_version": ip_version
    }

async def run_checker(input_file: str = "all_servers.txt"):
    if not os.path.exists(input_file):
        logger.error(f"File '{input_file}' not found.")
        return

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
        configs = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    logger.info(f"⚡ Testing {len(configs)} configs with Strict VIP filter (Ping < {MAX_PING_THRESHOLD_MS}ms)...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROBES)

    tasks = [check_single_config(cfg, semaphore) for cfg in configs]
    tested_candidates = []

    for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="[Testing Latency]"):
        res = await fut
        if res:
            tested_candidates.append(res)

    logger.info(f"✅ Active servers under {MAX_PING_THRESHOLD_MS}ms: {len(tested_candidates)}")

    if not tested_candidates:
        logger.warning("No servers met the < 500ms latency requirement.")
        Path(OUTPUT_TESTED_JSON).write_text("[]", encoding="utf-8")
        return

    # Extract unique IPs for batch GeoIP resolution
    unique_ips = list({c["ip"] for c in tested_candidates})
    logger.info(f"🌍 Resolving country, flag, and datacenter for {len(unique_ips)} unique IPs (100% Free)...")

    geo_resolver = FreeGeoResolver(GEO_CACHE_FILE)
    geo_map = await geo_resolver.resolve_ips(unique_ips)

    # Attach GeoIP details to tested candidates
    final_output = []
    for item in tested_candidates:
        geo = geo_map.get(item["ip"], {
            "country": "Global",
            "country_fa": "اینترنت آزاد",
            "country_code": "GL",
            "flag": "🌐",
            "city": "Global",
            "datacenter": "Cloud"
        })
        item.update(geo)
        final_output.append(item)

    # Sort strictly by lowest ping
    final_output.sort(key=lambda x: x["ping"])

    Path("data").mkdir(exist_ok=True)
    with open(OUTPUT_TESTED_JSON, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 Saved {len(final_output)} tested & categorized servers to '{OUTPUT_TESTED_JSON}'")

if __name__ == "__main__":
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    in_file = sys.argv[1] if len(sys.argv) > 1 else "all_servers.txt"
    asyncio.run(run_checker(in_file))
