#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - 5-Line Official Remark Formatter Engine
# Rule: Mandatory 5-line pattern for all protocols (including VMess)
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import base64
import logging
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("remarker")

INPUT_TESTED_JSON = "data/tested_servers.json"
OUTPUT_SERVERS_FILE = "all_servers.txt"

def safe_b64_decode(text: str) -> str:
    s = text.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def b64_encode_nopad(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8").rstrip("=")

def detect_real_capability(uri: str, scheme: str) -> str:
    """
    Detects the true network capability of the config based on security and transport parameters.
    """
    uri_lower = uri.lower()
    if "security=reality" in uri_lower or "pbk=" in uri_lower:
        return "Reality Bypass"
    if "type=grpc" in uri_lower:
        return "gRPC TLS"
    if scheme in ("hysteria", "hysteria2", "hy2"):
        return "UDP Fast-Path"
    if scheme in ("tuic", "juicity"):
        return "QUIC High-Speed"
    if "security=tls" in uri_lower:
        return "TLS Encrypted"
    if "type=ws" in uri_lower or "net=ws" in uri_lower:
        return "WebSocket CDN"
    if scheme in ("socks", "socks4", "socks5"):
        return "Emergency SOCKS5"
    return "VIP Strict"

def build_5line_remark(flag: str, country_fa: str, city_or_dc: str, ping: int,
                       capability: str, protocol: str, ip_version: str) -> str:
    """
    Constructs the exact 5-line Goodbaye Standard Remark:
    👉🆔@Goodbaye_filtering
    📡[پرچم کشور] [نام کشور]
    ®️[نام شهر یا دیتاسنتر]
    🅿️ping:[عدد پینگ]ms
    ⚡[قابلیت واقعی] | [نوع پروتکل و نسخه آی‌پی]
    """
    line1 = "👉🆔@Goodbaye_filtering"
    line2 = f"📡{flag} {country_fa}".strip()
    line3 = f"®️{city_or_dc}".strip()
    line4 = f"🅿️ping:{ping}ms"
    line5 = f"⚡{capability} | {protocol.upper()} {ip_version}".strip()

    return f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"

def apply_remark_to_vmess(uri: str, remark: str) -> str:
    """Injects the multiline 5-line remark into VMess JSON body."""
    try:
        payload = uri.split("://", 1)[1].split("#", 1)[0].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if not decoded:
            return uri
        data = json.loads(decoded)
        data["ps"] = remark  # Standard 5-line remark inside ps
        new_payload = b64_encode_nopad(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        return f"vmess://{new_payload}"
    except Exception:
        return uri

def apply_remark_to_generic(uri: str, remark: str) -> str:
    """URL-encodes the 5-line remark and attaches it as URI fragment."""
    clean_uri = uri.split("#", 1)[0].strip()
    encoded_tag = quote(remark, safe="")
    return f"{clean_uri}#{encoded_tag}"

def apply_remark(item: dict) -> str:
    raw_uri = item.get("raw_uri", "")
    scheme = item.get("scheme", "").lower()
    flag = item.get("flag", "🌐")
    country_fa = item.get("country_fa", "اینترنت آزاد")
    city = item.get("city", "")
    dc = item.get("datacenter", "Cloud")
    ping = item.get("ping", 100)
    ip_version = item.get("ip_version", "IPv4")

    # Clean location/datacenter label
    location_label = f"{city} - {dc}" if city and city != dc else (city or dc)
    capability = detect_real_capability(raw_uri, scheme)

    remark = build_5line_remark(
        flag=flag,
        country_fa=country_fa,
        city_or_dc=location_label,
        ping=ping,
        capability=capability,
        protocol=scheme,
        ip_version=ip_version
    )

    if scheme == "vmess":
        return apply_remark_to_vmess(raw_uri, remark)
    else:
        return apply_remark_to_generic(raw_uri, remark)

def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else INPUT_TESTED_JSON
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_SERVERS_FILE

    if not Path(json_path).exists():
        logger.error(f"Tested servers file '{json_path}' not found. Run checker.py first.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            servers = json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON: {e}")
            return

    if not servers:
        logger.warning("No tested servers to remark.")
        return

    logger.info(f"Applying Goodbaye 5-line remark standard to {len(servers)} servers...")
    remarked_configs = []

    for item in servers:
        try:
            formatted = apply_remark(item)
            if formatted:
                remarked_configs.append(formatted)
        except Exception as e:
            logger.debug(f"Error formatting item: {e}")

    # Save to primary all_servers.txt
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for cfg in remarked_configs:
            f.write(cfg + "\n")

    logger.info(f"✅ Successfully written {len(remarked_configs)} standard-compliant configs to '{output_path}'")

if __name__ == "__main__":
    main()
