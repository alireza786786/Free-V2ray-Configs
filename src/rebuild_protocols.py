#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol & Country Rebuilder
# Features: Strict Endpoint Deduplication (Zero Duplicates) + Auto Country Shards
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import base64
import logging
from pathlib import Path
from urllib.parse import quote, urlsplit

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rebuild_protocols")

ALL_SERVERS = "all_servers.txt"
SERVERS_DIR = "servers"
COUNTRIES_DIR = "servers/countries"

PROTO_MAP = {
    "hy2": "hysteria2",
    "VLESS": "vless",
    "shadowsocks": "ss",
    "socks": "socks5",
    "socks4": "socks5"
}

FA_COUNTRY_MAP = {
    "DE": ("🇩🇪", "آلمان", "germany"),
    "NL": ("🇳🇱", "هلند", "netherlands"),
    "US": ("🇺🇸", "آمریکا", "united_states"),
    "GB": ("🇬🇧", "انگلیس", "united_kingdom"),
    "FR": ("🇫🇷", "فرانسه", "france"),
    "TR": ("🇹🇷", "ترکیه", "turkey"),
    "FI": ("🇫🇮", "فنلاند", "finland"),
    "SE": ("🇸🇪", "سوئد", "sweden"),
    "CA": ("🇨🇦", "کانادا", "canada"),
    "SG": ("🇸🇬", "سنگاپور", "singapore"),
    "JP": ("🇯🇵", "ژاپن", "japan"),
    "AE": ("🇦🇪", "امارات", "united_arab_emirates"),
    "RU": ("🇷🇺", "روسیه", "russia"),
    "IR": ("🇮🇷", "ایران", "iran"),
    "IT": ("🇮🇹", "ایتالیا", "italy"),
    "PL": ("🇵🇱", "لهستان", "poland"),
    "CH": ("🇨🇭", "سوئیس", "switzerland"),
    "AT": ("🇦🇹", "اتریش", "austria")
}

def safe_b64_decode(text: str) -> str:
    s = text.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def b64_encode_nopad(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8").rstrip("=")

def extract_endpoint_signature(uri: str, scheme: str) -> tuple[str, str, int, str]:
    """
    Extracts a strict technical signature: (scheme, host, port, user_id)
    This guarantees ZERO duplicates regardless of query order, tags, or formatting.
    """
    clean_uri = uri.split("#", 1)[0].strip()
    host = ""
    port = 0
    identifier = ""

    if scheme == "vmess":
        payload = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                host = str(data.get("add", "")).lower().strip()
                port = int(data.get("port", 0))
                identifier = str(data.get("id", "")).lower().strip()
            except Exception:
                pass
    elif scheme == "ss":
        part = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        if "@" in part:
            cred, host_port = part.rsplit("@", 1)
            identifier = cred
            if ":" in host_port:
                h, p = host_port.rsplit(":", 1)
                host = h.strip("[]").lower()
                port = int(p) if p.isdigit() else 0
    else:
        try:
            parsed = urlsplit(clean_uri)
            host = (parsed.hostname or "").lower()
            port = parsed.port or 0
            identifier = (parsed.username or "").lower()
        except Exception:
            pass

    return clean_uri, host, port, identifier

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

def guess_location(host: str) -> tuple[str, str, str, str]:
    """Returns: (flag, country_fa, datacenter, country_slug)"""
    h = host.lower()
    flag, country_fa, country_slug = "🌐", "اینترنت آزاد", "global"
    dc = "Cloud Server"

    for code, (f, c_fa, slug) in FA_COUNTRY_MAP.items():
        if f".{code.lower()}" in h or slug in h:
            flag, country_fa, country_slug = f, c_fa, slug
            break

    if "cloudflare" in h or "pages.dev" in h or "workers.dev" in h:
        dc = "Cloudflare CDN"
    elif "hetzner" in h:
        dc = "Hetzner Online"
    elif "ovh" in h:
        dc = "OVHcloud"
    elif "digitalocean" in h:
        dc = "DigitalOcean"
    elif "amazon" in h or "aws" in h:
        dc = "AWS Cloud"
    elif host:
        clean = host.split(".")[0] if "." in host else host
        dc = f"{clean.capitalize()} DC"

    return flag, country_fa, dc, country_slug

def apply_goodbaye_remark(uri_clean: str, scheme: str, host: str) -> str:
    flag, country_fa, dc, country_slug = guess_location(host)
    capability = detect_capability(uri_clean, scheme)

    line1 = "👉🆔@Goodbaye_filtering"
    line2 = f"📡{flag} {country_fa}"
    line3 = f"®️{dc}"
    line4 = "🅿️ping:128ms"
    line5 = f"⚡{capability} | {scheme.upper()} IPv4"
    remark_text = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"

    if scheme == "vmess":
        payload = uri_clean.split("://", 1)[-1]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                data["ps"] = remark_text
                new_payload = b64_encode_nopad(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                return f"vmess://{new_payload}", country_slug
            except Exception:
                pass
        return uri_clean, country_slug
    else:
        encoded_remark = quote(remark_text, safe="")
        return f"{uri_clean}#{encoded_remark}", country_slug

def main():
    if not os.path.exists(ALL_SERVERS):
        logger.error(f"{ALL_SERVERS} not found!")
        return

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    logger.info(f"Read {len(raw_lines)} candidate configs. Starting strict deduplication...")

    os.makedirs(SERVERS_DIR, exist_ok=True)
    os.makedirs(COUNTRIES_DIR, exist_ok=True)

    # Clean existing country files to prevent stale/duplicate country files
    for old_country_file in Path(COUNTRIES_DIR).glob("*.txt"):
        try:
            old_country_file.unlink()
        except Exception:
            pass

    seen_endpoints = set()
    unique_remarked_all = []
    protocol_groups = {}
    country_groups = {}

    for cfg in raw_lines:
        if "://" not in cfg:
            continue

        raw_scheme = cfg.split("://", 1)[0].strip().lower()
        proto = PROTO_MAP.get(raw_scheme, raw_scheme)

        clean_uri, host, port, identifier = extract_endpoint_signature(cfg, proto)
        if not host:
            continue

        # Strict Unique Endpoint Signature (Eliminates ALL duplicates)
        sig = (proto, host, port, identifier)
        if sig in seen_endpoints:
            continue
        seen_endpoints.add(sig)

        # Normalize URI scheme
        if raw_scheme != proto:
            clean_uri = clean_uri.replace(f"{raw_scheme}://", f"{proto}://", 1)

        # Apply Goodbaye 5-Line Remark
        remarked_cfg, country_slug = apply_goodbaye_remark(clean_uri, proto, host)

        unique_remarked_all.append(remarked_cfg)
        protocol_groups.setdefault(proto, []).append(remarked_cfg)
        country_groups.setdefault(country_slug, []).append(remarked_cfg)

    # 1. Update all_servers.txt (Strictly Unique)
    with open(ALL_SERVERS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(unique_remarked_all) + "\n")
    logger.info(f"✅ all_servers.txt updated: {len(unique_remarked_all)} completely UNIQUE configs (0 duplicates).")

    # 2. Write Protocol files
    for p, items in protocol_groups.items():
        fname = f"{SERVERS_DIR}/{p}_servers.txt"
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")
        logger.info(f"   ↳ {p}_servers.txt: {len(items)} configs")

    # 3. Write Country files in servers/countries/
    for c_slug, items in country_groups.items():
        fname = f"{COUNTRIES_DIR}/{c_slug}.txt"
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")

    logger.info(f"✅ Successfully updated {len(country_groups)} country files in '{COUNTRIES_DIR}'.")

if __name__ == "__main__":
    main()
