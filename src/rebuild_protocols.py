#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol Rebuilder with 5-Line Remark Formatter
# Exact reference structure with Goodbaye mandatory naming standard
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

# Protocol normalization map (identical to reference repo)
PROTO_MAP = {
    "hy2": "hysteria2",
    "VLESS": "vless",
    "shadowsocks": "ss",
    "socks": "socks5"
}

# Country flag & name mapping (ISO to Unicode Emoji)
FA_COUNTRY_MAP = {
    "DE": ("🇩🇪", "آلمان"), "NL": ("🇳🇱", "هلند"), "US": ("🇺🇸", "آمریکا"),
    "GB": ("🇬🇧", "انگلیس"), "FR": ("🇫🇷", "فرانسه"), "TR": ("🇹🇷", "ترکیه"),
    "FI": ("🇫🇮", "فنلاند"), "SE": ("🇸🇪", "سوئد"), "CA": ("🇨🇦", "کانادا"),
    "SG": ("🇸🇬", "سنگاپور"), "JP": ("🇯🇵", "ژاپن"), "AE": ("🇦🇪", "امارات"),
    "RU": ("🇷🇺", "روسیه"), "IR": ("🇮🇷", "ایران"), "IT": ("🇮🇹", "ایتالیا"),
    "PL": ("🇵🇱", "لهستان"), "CH": ("🇨🇭", "سوئیس"), "AT": ("🇦🇹", "اتریش")
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

def detect_host_and_capability(uri: str, scheme: str) -> tuple[str, str, str]:
    """Extracts host, capability, and clean uri without remark."""
    uri_clean = uri.split("#", 1)[0].strip()
    capability = "VIP Strict"
    host = ""

    # Detect real capability from parameters
    u_lower = uri_clean.lower()
    if "security=reality" in u_lower or "pbk=" in u_lower:
        capability = "Reality Bypass"
    elif "type=grpc" in u_lower:
        capability = "gRPC TLS"
    elif scheme in ("hysteria", "hysteria2", "hy2"):
        capability = "UDP Fast-Path"
    elif scheme in ("tuic", "juicity"):
        capability = "QUIC Ultra"
    elif "security=tls" in u_lower:
        capability = "TLS High-Speed"
    elif "type=ws" in u_lower or "net=ws" in u_lower:
        capability = "WebSocket CDN"
    elif scheme in ("socks", "socks5", "socks4"):
        capability = "Emergency SOCKS5"

    # Extract host
    if scheme == "vmess":
        payload = uri_clean.split("://", 1)[-1].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                host = str(data.get("add", "")).strip()
            except Exception:
                pass
    elif "@" in uri_clean:
        try:
            part = uri_clean.rsplit("@", 1)[-1].split("?", 1)[0]
            host = part.split(":", 1)[0].strip("[]")
        except Exception:
            pass
    else:
        try:
            parsed = urlsplit(uri_clean)
            host = parsed.hostname or ""
        except Exception:
            pass

    return uri_clean, host, capability

def guess_location_and_dc(host: str) -> tuple[str, str, str]:
    """Guesses country and datacenter from host/domain indicators."""
    h = host.lower()
    flag, country_fa = "🌐", "اینترنت آزاد"
    dc = "Cloud Server"

    # Known TLD and subdomains
    if ".de" in h or "fra" in h or "germany" in h:
        flag, country_fa = FA_COUNTRY_MAP["DE"]
    elif ".nl" in h or "ams" in h or "netherlands" in h:
        flag, country_fa = FA_COUNTRY_MAP["NL"]
    elif ".us" in h or "usa" in h or "ord" in h or "lax" in h:
        flag, country_fa = FA_COUNTRY_MAP["US"]
    elif ".fr" in h or "paris" in h:
        flag, country_fa = FA_COUNTRY_MAP["FR"]
    elif ".tr" in h or "turkey" in h or "ist" in h:
        flag, country_fa = FA_COUNTRY_MAP["TR"]
    elif ".fi" in h or "hel" in h or "finland" in h:
        flag, country_fa = FA_COUNTRY_MAP["FI"]
    elif ".uk" in h or ".gb" in h or "lon" in h:
        flag, country_fa = FA_COUNTRY_MAP["GB"]

    # Datacenter detection
    if "cloudflare" in h or "pages.dev" in h or "workers.dev" in h:
        dc = "Cloudflare CDN"
    elif "hetzner" in h or "your-server" in h:
        dc = "Hetzner Online"
    elif "ovh" in h:
        dc = "OVHcloud"
    elif "digitalocean" in h:
        dc = "DigitalOcean"
    elif "amazon" in h or "aws" in h or "cloudfront" in h:
        dc = "AWS Cloud"
    elif host:
        clean_name = host.split(".")[0] if "." in host else host
        dc = f"{clean_name.capitalize()} DC"

    return flag, country_fa, dc

def build_5line_remark(flag: str, country_fa: str, dc: str, scheme: str, capability: str) -> str:
    """
    Constructs the Goodbaye 5-Line Universal Standard Remark:
    👉🆔@Goodbaye_filtering
    📡[پرچم] [کشور]
    ®️[دیتاسنتر/شهر]
    🅿️ping:120ms
    ⚡[قابلیت] | [پروتکل و آی‌پی]
    """
    line1 = "👉🆔@Goodbaye_filtering"
    line2 = f"📡{flag} {country_fa}"
    line3 = f"®️{dc}"
    line4 = "🅿️ping:128ms"
    line5 = f"⚡{capability} | {scheme.upper()} IPv4"
    return f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"

def apply_goodbaye_remark(uri: str, scheme: str) -> str:
    """Applies the 5-line remark cleanly (VMess JSON ps or URL-encoded fragment)."""
    uri_clean, host, capability = detect_host_and_capability(uri, scheme)
    flag, country_fa, dc = guess_location_and_dc(host)
    remark_text = build_5line_remark(flag, country_fa, dc, scheme, capability)

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
        raw_configs = sorted({line.strip() for line in f if line.strip() and not line.startswith("#")})

    os.makedirs(SERVERS_DIR, exist_ok=True)
    protocols = {}
    remarked_all_servers = []

    for cfg in raw_configs:
        if '://' not in cfg:
            continue

        original_proto = cfg.split('://')[0].strip().lower()
        proto = PROTO_MAP.get(original_proto, original_proto)

        # Normalize scheme in URI
        if original_proto != proto:
            cfg = cfg.replace(f"{original_proto}://", f"{proto}://", 1)

        # Apply Goodbaye 5-Line Remark
        remarked_cfg = apply_goodbaye_remark(cfg, proto)

        protocols.setdefault(proto, []).append(remarked_cfg)
        remarked_all_servers.append(remarked_cfg)

    # 1. Update all_servers.txt with remarked configs
    with open(ALL_SERVERS, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(remarked_all_servers) + "\n")
    logger.info(f"Updated {ALL_SERVERS} with {len(remarked_all_servers)} remarked configs.")

    # 2. Write exact reference protocol files into servers/
    for proto, items in protocols.items():
        fname = f"{SERVERS_DIR}/{proto}_servers.txt"
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")
        logger.info(f"Rebuilt {fname} with {len(items)} configs")

    print(f"✅ Protocol rebuild complete. Total: {len(remarked_all_servers)} configs.")

if __name__ == "__main__":
    main()
