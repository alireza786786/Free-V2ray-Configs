#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol & Worldwide Country Rebuilder
# Features: True GeoIP (Japan, Sweden, USA, Russia, Turkey, Malaysia, etc.)
#           Strict Endpoint Deduplication (Zero Duplicates)
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import socket
import base64
import logging
from pathlib import Path
from urllib.parse import quote, urlsplit
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rebuild_protocols")

ALL_SERVERS = "all_servers.txt"
SERVERS_DIR = "servers"
COUNTRIES_DIR = "servers/countries"
GEO_CACHE_FILE = "data/geoip_cache.json"

PROTO_MAP = {
    "hy2": "hysteria2",
    "VLESS": "vless",
    "shadowsocks": "ss",
    "socks": "socks5",
    "socks4": "socks5"
}

# Complete Persian Translations for Worldwide Countries
COUNTRY_FA_MAP = {
    "JP": ("🇯🇵", "ژاپن", "japan"),
    "SE": ("🇸🇪", "سوئد", "sweden"),
    "US": ("🇺🇸", "آمریکا", "united_states"),
    "RU": ("🇷🇺", "روسیه", "russia"),
    "TR": ("🇹🇷", "ترکیه", "turkey"),
    "MY": ("🇲🇾", "مالزی", "malaysia"),
    "SG": ("🇸🇬", "سنگاپور", "singapore"),
    "DE": ("🇩🇪", "آلمان", "germany"),
    "NL": ("🇳🇱", "هلند", "netherlands"),
    "GB": ("🇬🇧", "انگلیس", "united_kingdom"),
    "FR": ("🇫🇷", "فرانسه", "france"),
    "FI": ("🇫🇮", "فنلاند", "finland"),
    "CA": ("🇨🇦", "کانادا", "canada"),
    "AE": ("🇦🇪", "امارات", "united_arab_emirates"),
    "IT": ("🇮🇹", "ایتالیا", "italy"),
    "ES": ("🇪🇸", "اسپانیا", "spain"),
    "PL": ("🇵🇱", "لهستان", "poland"),
    "CH": ("🇨🇭", "سوئیس", "switzerland"),
    "AT": ("🇦🇹", "اتریش", "austria"),
    "NO": ("🇳🇴", "نروژ", "norway"),
    "DK": ("🇩🇰", "دانمارک", "denmark"),
    "BE": ("🇧🇪", "بلژیک", "belgium"),
    "IR": ("🇮🇷", "ایران", "iran"),
    "UA": ("🇺🇦", "اوکراین", "ukraine"),
    "AU": ("🇦🇺", "استرالیا", "australia"),
    "IN": ("🇮🇳", "هند", "india"),
    "KR": ("🇰🇷", "کره جنوبی", "south_korea"),
    "HK": ("🇭🇰", "هنگ کنگ", "hong_kong"),
    "TW": ("🇹🇼", "تایوان", "taiwan"),
    "BR": ("🇧🇷", "برزیل", "brazil"),
    "ZA": ("🇿🇦", "آفریقای جنوبی", "south_africa"),
    "IE": ("🇮🇪", "ایرلند", "ireland"),
    "RO": ("🇷🇴", "رومانی", "romania"),
    "CZ": ("🇨🇿", "جمهوری چک", "czech_republic")
}

def country_code_to_flag(code: str) -> str:
    if not code or len(code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c.upper())) for c in code)

def safe_b64_decode(text: str) -> str:
    s = text.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def b64_encode_nopad(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8").rstrip("=")

def extract_endpoint_signature(uri: str, scheme: str) -> tuple[str, str, int]:
    """
    Extracts the physical server signature: (protocol, host/ip, port)
    Guarantees that a server endpoint is only added ONCE (Zero Duplicates).
    """
    clean_uri = uri.split("#", 1)[0].strip()
    host = ""
    port = 0

    if scheme == "vmess":
        payload = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                host = str(data.get("add", "")).lower().strip()
                port = int(data.get("port", 0))
            except Exception:
                pass
    elif scheme == "ss":
        part = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        if "@" in part:
            _, host_port = part.rsplit("@", 1)
            if ":" in host_port:
                h, p = host_port.rsplit(":", 1)
                host = h.strip("[]").lower().strip()
                port = int(p) if p.isdigit() else 0
    else:
        try:
            parsed = urlsplit(clean_uri)
            host = (parsed.hostname or "").lower().strip()
            port = parsed.port or 0
        except Exception:
            pass

    return clean_uri, host, port

def resolve_ip(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host

class GeoIPManager:
    """100% Free Persistent GeoIP resolver with batch querying."""
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = {}
        self._load()

    def _load(self):
        if Path(self.cache_file).exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save(self):
        try:
            Path("data").mkdir(exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Error saving GeoIP cache: {e}")

    def resolve_batch(self, ips: list[str]):
        unresolved = [ip for ip in ips if ip not in self.cache and not ip.startswith("104.") and not ip.startswith("172.")]
        if not unresolved:
            return

        for i in range(0, len(unresolved), 100):
            batch = unresolved[i:i + 100]
            try:
                resp = requests.post("http://ip-api.com/batch?fields=status,country,countryCode,city,org,as,query", json=batch, timeout=10)
                if resp.status_code == 200:
                    for item in resp.json():
                        q_ip = item.get("query")
                        if item.get("status") == "success":
                            cc = item.get("countryCode", "GL")
                            c_name = item.get("country", "Global")
                            org = item.get("org", "") or item.get("as", "")
                            self.cache[q_ip] = {
                                "cc": cc,
                                "country": c_name,
                                "org": org.split()[1] if "AS" in org and len(org.split()) > 1 else (org[:16] or "Cloud")
                            }
            except Exception as e:
                logger.debug(f"GeoIP API error: {e}")
                break

        self.save()

    def get_info(self, ip: str, host: str) -> tuple[str, str, str, str]:
        # Fast Cloudflare check
        if host.endswith(".pages.dev") or host.endswith(".workers.dev") or "cloudflare" in host:
            return "🌐", "اینترنت آزاد", "Cloudflare CDN", "global"

        info = self.cache.get(ip, {})
        cc = info.get("cc", "")
        if cc in COUNTRY_FA_MAP:
            flag, c_fa, slug = COUNTRY_FA_MAP[cc]
        elif cc:
            flag = country_code_to_flag(cc)
            c_fa = info.get("country", "اینترنت آزاد")
            slug = info.get("country", "global").lower().replace(" ", "_")
        else:
            flag, c_fa, slug = "🌐", "اینترنت آزاد", "global"

        dc = info.get("org", "Cloud Server")
        return flag, c_fa, dc, slug

def detect_capability(uri_clean: str, scheme: str) -> str:
    u = uri_clean.lower()
    if "security=reality" in u or "pbk=" in u:
        return "Reality Bypass"
    if "type=grpc" in u:
        return "gRPC TLS"
    if scheme in ("hysteria", "hysteria2", "hy2"):
        return "UDP Fast-Path"
    if scheme in ("tuic", "juicity"):
        return "QUIC Ultra"
    if "security=tls" in u:
        return "TLS High-Speed"
    if "type=ws" in u or "net=ws" in u:
        return "WebSocket CDN"
    if scheme in ("socks", "socks5", "socks4"):
        return "Emergency SOCKS5"
    return "VIP Strict"

def build_5line_remark(flag: str, country_fa: str, dc: str, scheme: str, capability: str) -> str:
    line1 = "👉🆔@Goodbaye_filtering"
    line2 = f"📡{flag} {country_fa}"
    line3 = f"®️{dc}"
    line4 = "🅿️ping:128ms"
    line5 = f"⚡{capability} | {scheme.upper()} IPv4"
    return f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"

def apply_goodbaye_remark(uri_clean: str, scheme: str, flag: str, c_fa: str, dc: str) -> str:
    capability = detect_capability(uri_clean, scheme)
    remark_text = build_5line_remark(flag, c_fa, dc, scheme, capability)

    if scheme == "vmess":
        payload = uri_clean.split("://", 1)[-1]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                data["ps"] = remark_text
                new_payload = b64_encode_nopad(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                return f"vmess://{new_payload}"
            except Exception:
                pass
        return uri_clean
    else:
        encoded_remark = quote(remark_text, safe="")
        return f"{uri_clean}#{encoded_remark}"

def main():
    if not os.path.exists(ALL_SERVERS):
        logger.error(f"{ALL_SERVERS} not found!")
        return

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    logger.info(f"Loaded {len(raw_lines)} candidate servers. Starting strict unique filtering...")

    os.makedirs(SERVERS_DIR, exist_ok=True)
    os.makedirs(COUNTRIES_DIR, exist_ok=True)

    # Clean existing country files
    for old_f in Path(COUNTRIES_DIR).glob("*.txt"):
        try:
            old_f.unlink()
        except Exception:
            pass

    seen_endpoints = set()
    unique_candidates = []

    for cfg in raw_lines:
        if "://" not in cfg:
            continue

        raw_scheme = cfg.split("://", 1)[0].strip().lower()
        proto = PROTO_MAP.get(raw_scheme, raw_scheme)

        clean_uri, host, port = extract_endpoint_signature(cfg, proto)
        if not host or port <= 0:
            continue

        # Strict Unique Key (protocol, host, port) -> ZERO Duplicates
        sig = (proto, host, port)
        if sig in seen_endpoints:
            continue
        seen_endpoints.add(sig)

        unique_candidates.append({
            "clean_uri": clean_uri,
            "raw_scheme": raw_scheme,
            "proto": proto,
            "host": host,
            "port": port
        })

    logger.info(f"Strict Deduplication completed: {len(unique_candidates)} unique endpoints found.")

    # Resolve IPs and GeoIP in batch
    geo_mgr = GeoIPManager(GEO_CACHE_FILE)
    ips_to_query = list({resolve_ip(item["host"]) for item in unique_candidates})
    geo_mgr.resolve_batch(ips_to_query)

    remarked_all = []
    protocol_groups = {}
    country_groups = {}

    for item in unique_candidates:
        clean_uri = item["clean_uri"]
        proto = item["proto"]
        host = item["host"]
        ip = resolve_ip(host)

        flag, c_fa, dc, country_slug = geo_mgr.get_info(ip, host)

        if item["raw_scheme"] != proto:
            clean_uri = clean_uri.replace(f"{item['raw_scheme']}://", f"{proto}://", 1)

        remarked = apply_goodbaye_remark(clean_uri, proto, flag, c_fa, dc)

        remarked_all.append(remarked)
        protocol_groups.setdefault(proto, []).append(remarked)
        country_groups.setdefault(country_slug, []).append(remarked)

    # 1. Write unique all_servers.txt
    with open(ALL_SERVERS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(remarked_all) + "\n")
    logger.info(f"✅ all_servers.txt updated: {len(remarked_all)} strictly unique configs.")

    # 2. Write Protocol files
    for p, items in protocol_groups.items():
        fname = f"{SERVERS_DIR}/{p}_servers.txt"
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")

    # 3. Write Country files (Japan, Sweden, USA, Russia, Turkey, Malaysia, etc.)
    for slug, items in country_groups.items():
        if slug == "global" and len(items) > 300:
            continue  # Keep countries focused
        fname = f"{COUNTRIES_DIR}/{slug}.txt"
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")

    logger.info(f"✅ Successfully sharded {len(country_groups)} country files in '{COUNTRIES_DIR}'.")

if __name__ == "__main__":
    main()
