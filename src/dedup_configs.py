#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol-Aware Semantic Deduplication
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("dedup_configs")

# Canonicalization policy: Keys stripped to prepare for Goodbaye 5-line remark
IGNORED_REMARK_KEYS = {"ps", "remark", "alias", "name", "tag"}

# Case-insensitive values in share links
LOWER_VALUE_KEYS = {
    "type", "security", "fp", "alpn", "sni", "flow",
    "encryption", "headertype", "network", "net", "tls",
    "scy", "mode", "proto"
}

# Host parameters normalized to lowercase
HOST_VALUE_KEYS = {"add", "host", "sni", "server", "servername", "address"}

# Case-insensitive UUID / Identity fields
UUID_VALUE_KEYS = {"id", "uuid"}

# Number-like fields standardizing to integer strings
STRING_NUMBER_KEYS = {
    "port", "aid", "alterid", "mtu", "tti", "udpport",
    "tcpport", "packetencoding"
}

SCHEME_ALIASES = {
    "shadowsocks": "ss",
    "socks5": "socks",
    "socks4": "socks",
    "hy2": "hysteria2",
}

BASE64_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")

def safe_b64_decode_text(text: str) -> Optional[bytes]:
    """Decode standard or URL-safe base64, with or without padding."""
    s = re.sub(r"\s+", "", text or "")
    if not s:
        return None
    candidates = (s, s + "=" * (-len(s) % 4))
    for candidate in candidates:
        for decoder in (base64.urlsafe_b64decode, base64.b64decode):
            try:
                return decoder(candidate.encode("utf-8"))
            except Exception:
                continue
    return None

def b64_encode_nopad(data: bytes) -> str:
    """Encode bytes into base64 string without trailing padding."""
    return base64.b64encode(data).decode("utf-8").rstrip("=")

def is_probably_base64_line(text: str) -> bool:
    s = re.sub(r"\s+", "", text or "")
    if len(s) < 16 or any(c in s for c in ("://", "@", "#", "?")):
        return False
    return bool(BASE64_RE.fullmatch(s))

def decode_subscription_payload_if_needed(text: str) -> str:
    """Decode file content if the whole content is base64 encoded."""
    raw = text.strip()
    if not raw or "://" in raw:
        return text
    decoded = safe_b64_decode_text(raw)
    if not decoded:
        return text
    decoded_text = decoded.decode("utf-8", errors="ignore")
    return decoded_text if "://" in decoded_text else text

def parse_host_port(host_port: str) -> tuple[str, Optional[int]]:
    """Parse host[:port], supporting IPv6 bracket notation."""
    s = (host_port or "").strip()
    if not s:
        return "", None

    if s.startswith("["):
        end = s.find("]")
        if end == -1:
            return s.lower(), None
        host = s[1:end].lower()
        rest = s[end + 1:]
        if rest.startswith(":"):
            port_str = rest[1:].strip()
            if port_str.isdigit():
                return host, int(port_str)
        return host, None

    if s.count(":") == 1:
        host, port_str = s.rsplit(":", 1)
        host = host.lower().strip()
        if port_str.isdigit():
            return host, int(port_str)
        return host, None

    return s.lower(), None

def normalize_scalar(key: str, value: Any, *, lower_sensitive: bool = False) -> Any:
    """Normalize a scalar value for deterministic deduplication."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return str(int(value)) if key in STRING_NUMBER_KEYS else value
    if isinstance(value, str):
        s = value.strip()
        if key in UUID_VALUE_KEYS or lower_sensitive or key in HOST_VALUE_KEYS or key in LOWER_VALUE_KEYS:
            return s.lower()
        if key in STRING_NUMBER_KEYS and s.isdigit():
            return str(int(s))
        return s
    if isinstance(value, list):
        return [normalize_scalar(key, item, lower_sensitive=lower_sensitive) for item in value]
    if isinstance(value, dict):
        items = []
        for k, v in value.items():
            lk = str(k).strip().lower()
            if lk in IGNORED_REMARK_KEYS:
                continue
            items.append((lk, normalize_scalar(lk, v)))
        items.sort(key=lambda x: (x[0], json.dumps(x[1], ensure_ascii=False, sort_keys=True, separators=(",", ":"))))
        return {k: v for k, v in items}
    return str(value).strip()

def canonical_query_pairs(query: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(query, keep_blank_values=True, strict_parsing=False):
        lk = key.strip().lower()
        if lk in IGNORED_REMARK_KEYS:
            continue
        nv = normalize_scalar(lk, value)
        if isinstance(nv, str):
            pairs.append((lk, nv))
        else:
            pairs.append((lk, json.dumps(nv, ensure_ascii=False, sort_keys=True, separators=(",", ":"))))
    pairs.sort(key=lambda x: (x[0], x[1]))
    return pairs

def build_uri(scheme: str, userinfo: Optional[str], host: str, port: Optional[int],
              path: str = "", query_pairs: Optional[list[tuple[str, str]]] = None, fragment: str = "") -> str:
    netloc = ""
    if userinfo:
        netloc += quote(userinfo, safe="") + "@"
    if host:
        netloc += f"[{host}]" if ":" in host and not host.startswith("[") else host.lower()
    if port is not None:
        netloc += f":{int(port)}"
    query = urlencode(query_pairs or [], doseq=True) if query_pairs else ""
    return urlunsplit((scheme, netloc, path or "", query, fragment or ""))

def normalize_vmess(raw: str) -> tuple[Optional[str], Optional[str]]:
    if "://" not in raw:
        return None, None
    payload = raw.split("://", 1)[1].strip()
    decoded = safe_b64_decode_text(payload)
    if not decoded:
        return None, None
    try:
        obj = json.loads(decoded.decode("utf-8", errors="ignore"))
    except Exception:
        return None, None
    if not isinstance(obj, dict):
        return None, None

    normalized: dict[str, Any] = {}
    for k, v in obj.items():
        lk = str(k).strip().lower()
        if lk in IGNORED_REMARK_KEYS:
            continue
        normalized[lk] = normalize_scalar(lk, v, lower_sensitive=(lk == "id"))

    key_json = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    rewrite_obj = {k: str(v) if k in STRING_NUMBER_KEYS and v is not None else v for k, v in normalized.items()}
    canonical_uri = f"vmess://{b64_encode_nopad(json.dumps(rewrite_obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))}"
    return key_json, canonical_uri

def normalize_ss(raw: str) -> tuple[Optional[str], Optional[str]]:
    if "://" not in raw:
        return None, None
    _, rest = raw.split("://", 1)
    if "#" in rest:
        rest, _ = rest.split("#", 1)
    query = ""
    if "?" in rest:
        rest, query = rest.split("?", 1)

    host, port, method, password = "", None, "", ""
    query_pairs = canonical_query_pairs(query)

    if "@" in rest:
        cred_part, host_port = rest.rsplit("@", 1)
        host, port = parse_host_port(host_port)
        decoded = safe_b64_decode_text(cred_part)
        cred_text = decoded.decode("utf-8", errors="ignore") if decoded else cred_part
        if ":" in cred_text:
            method, password = cred_text.split(":", 1)
            method, password = method.strip().lower(), password.strip()
        else:
            method = cred_part.strip().lower()
    else:
        decoded = safe_b64_decode_text(rest)
        if decoded:
            decoded_text = decoded.decode("utf-8", errors="ignore")
            if "@" in decoded_text and ":" in decoded_text:
                cred_part, host_port = decoded_text.rsplit("@", 1)
                host, port = parse_host_port(host_port)
                method, password = cred_part.split(":", 1)
                method, password = method.strip().lower(), password.strip()

    key_obj = {"scheme": "ss", "method": method, "password": password, "host": host.lower(), "port": port, "query": query_pairs} if host else {"scheme": "ss", "raw": rest.strip(), "query": query_pairs}
    key = json.dumps(key_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    canonical_uri = None
    if host and port is not None and method:
        userinfo = b64_encode_nopad(f"{method}:{password}".encode("utf-8"))
        canonical_uri = build_uri("ss", userinfo, host.lower(), port, "", query_pairs, "")
    elif host:
        canonical_uri = build_uri("ss", None, host.lower(), port, "", query_pairs, "")
    return key, canonical_uri

def normalize_generic(raw: str, scheme_in: str) -> tuple[Optional[str], Optional[str]]:
    if "://" not in raw:
        return None, None
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None, None

    scheme = SCHEME_ALIASES.get(parsed.scheme.lower(), parsed.scheme.lower()) or scheme_in.lower()
    if not scheme:
        return None, None
    try:
        port = parsed.port
    except ValueError:
        return None, None

    userinfo = (parsed.username or "").lower() if scheme == "vless" else (parsed.username or "")
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query_pairs = canonical_query_pairs(parsed.query)

    key_obj = {"scheme": scheme, "userinfo": userinfo, "host": host, "port": port, "path": path, "query": query_pairs}
    key = json.dumps(key_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    try:
        canonical_uri = build_uri(scheme, userinfo or None, host, port, path, query_pairs, "")
    except Exception:
        return None, None

    return key, canonical_uri

def normalize_config(raw: str) -> tuple[Optional[str], Optional[str]]:
    line = (raw or "").strip()
    if not line or line.startswith("#") or "://" not in line:
        return None, None

    scheme = line.split("://", 1)[0].strip().lower()
    scheme = SCHEME_ALIASES.get(scheme, scheme)

    if scheme == "vmess":
        return normalize_vmess(line)
    if scheme == "ss":
        return normalize_ss(line)
    return normalize_generic(line, scheme)

@dataclass
class StoredConfig:
    raw: str
    canonical: str

def load_candidate_lines(input_path: str) -> list[str]:
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    if "://" not in text:
        decoded = decode_subscription_payload_if_needed(text)
        if decoded != text:
            text = decoded

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if "://" not in line and is_probably_base64_line(line):
            decoded = safe_b64_decode_text(line)
            if decoded:
                decoded_text = decoded.decode("utf-8", errors="ignore")
                if "://" in decoded_text:
                    for sub in decoded_text.splitlines():
                        sub = sub.strip()
                        if sub and not sub.startswith("#"):
                            lines.append(sub)
                    continue
        lines.append(line)
    return lines

def process_servers(input_path: str, output_path: str, *, rewrite: bool = False, sort_output: bool = False) -> None:
    logger.info("Deduplicating %s", input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    lines = load_candidate_lines(input_path)
    unique: OrderedDict[str, StoredConfig] = OrderedDict()
    stats: Counter[str] = Counter()
    invalid = 0

    for raw_link in lines:
        if not raw_link or raw_link.startswith("#"):
            continue
        proto = raw_link.split("://", 1)[0].lower() if "://" in raw_link else "unknown"
        proto = SCHEME_ALIASES.get(proto, proto)

        canonical, normalized_uri = normalize_config(raw_link)
        if canonical is None:
            invalid += 1
            continue

        if canonical not in unique:
            unique[canonical] = StoredConfig(raw=raw_link, canonical=normalized_uri or raw_link)
            stats[proto] += 1

    items = list(unique.items())
    if sort_output:
        items.sort(key=lambda kv: kv[0])

    with open(output_path, "w", encoding="utf-8") as f:
        for _, record in items:
            f.write((record.canonical if rewrite else record.raw).rstrip() + "\n")

    logger.info("Total Read: %d, Invalid: %d, Unique Cleaned: %d", len(lines), invalid, len(unique))
    for proto, count in stats.most_common():
        logger.info("   ↳ %s: %d", proto, count)

def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical Deduplication for V2Ray & Proxies")
    parser.add_argument("input_file", help="Input file path containing proxies")
    parser.add_argument("-o", "--output", help="Output file path. Default: overwrite input", default=None)
    parser.add_argument("--rewrite", action="store_true", help="Write normalized links stripping old garbage remarks")
    parser.add_argument("--sort-output", action="store_true", help="Sort output deterministically")

    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output or f"{input_file}.tmp"

    process_servers(input_file, output_file, rewrite=args.rewrite, sort_output=args.sort_output)
    if args.output is None:
        os.replace(output_file, input_file)

if __name__ == "__main__":
    main()
