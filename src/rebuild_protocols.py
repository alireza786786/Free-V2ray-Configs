#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol & Worldwide Country Rebuilder  (v3)
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import re
import sys
import json
import time
import base64
import socket
import queue
import logging
import threading
import ipaddress
import argparse
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("rebuild_protocols")

ALL_SERVERS = "all_servers.txt"
SERVERS_DIR = "servers"
COUNTRIES_DIR = "servers/countries"
GEO_CACHE_FILE = "data/geoip_cache.json"

DNS_WORKERS = 128
DNS_DEADLINE = 150
GEO_BUDGET = 900
GEO_MIN_INTERVAL = 4.2
HOST_TTL = 7 * 86400
GEO_TTL = 60 * 86400
GEO_NEG_TTL = 3 * 86400

PROTO_MAP = {
    "hy2": "hysteria2",
    "VLESS": "vless",
    "shadowsocks": "ss",
    "socks": "socks5",
    "socks4": "socks5",
}

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
    "CZ": ("🇨🇿", "جمهوری چک", "czech_republic"),
}

IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

CF_FALLBACK_CIDRS = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]


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


def _split_host_port(host_port: str):
    host_port = host_port.strip()
    if host_port.startswith("["):
        host, _, rest = host_port[1:].partition("]")
        port = rest.lstrip(":")
        return host.lower(), (int(port) if port.isdigit() else 0)
    if host_port.count(":") == 1:
        h, p = host_port.rsplit(":", 1)
        return h.strip("[]").lower(), (int(p) if p.isdigit() else 0)
    return host_port.strip("[]").lower(), 0


def extract_endpoint_signature(uri: str, scheme: str):
    clean_uri = uri.split("#", 1)[0].strip()
    host, port = "", 0

    if scheme == "vmess":
        payload = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        data = None
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
            except Exception:
                data = None
        if isinstance(data, dict):
            host = str(data.get("add", "")).strip("[]").lower()
            try:
                port = int(str(data.get("port", 0)).strip() or 0)
            except Exception:
                port = 0
        return clean_uri, host, port

    if scheme == "ss":
        part = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        if "@" in part:
            _, host_port = part.rsplit("@", 1)
            host, port = _split_host_port(host_port)
        else:
            decoded = safe_b64_decode(part)
            if "@" in decoded:
                _, host_port = decoded.rsplit("@", 1)
                host, port = _split_host_port(host_port)
        return clean_uri, host, port

    if scheme == "ssr":
        decoded = safe_b64_decode(clean_uri.split("://", 1)[-1].split("?", 1)[0])
        if ":" in decoded:
            host, port = _split_host_port(":".join(decoded.split(":")[:2]))
        return clean_uri, host, port

    try:
        parsed = urlsplit(clean_uri)
        return clean_uri, (parsed.hostname or "").strip("[]").lower(), (parsed.port or 0)
    except Exception:
        return clean_uri, "", 0


def resolve_hosts(hosts, workers=DNS_WORKERS, deadline_s=DNS_DEADLINE):
    resolved = {}
    pending = []
    for h in hosts:
        if IPV4_RE.match(h):
            resolved[h] = h
        else:
            pending.append(h)

    if not pending:
        return resolved

    q = queue.Queue()
    for h in pending:
        q.put(h)
    lock = threading.Lock()

    def worker():
        while True:
            try:
                h = q.get_nowait()
            except queue.Empty:
                return
            try:
                ip = socket.gethostbyname(h)
            except Exception:
                ip = None
            with lock:
                resolved[h] = ip

    n = min(workers, len(pending))
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=max(0.0, deadline_s - (time.time() - start)))

    unresolved_missing = 0
    with lock:
        for h in pending:
            if h not in resolved:
                resolved[h] = None
                unresolved_missing += 1

    ok = sum(1 for h in pending if resolved.get(h))
    logger.info("DNS: %d hostnames -> %d resolved, %d failed, %d skipped at deadline (%.1fs)",
                len(pending), ok, len(pending) - ok - unresolved_missing,
                unresolved_missing, time.time() - start)
    return resolved


class GeoIPManager:
    def __init__(self, cache_file: str, budget_s: float = GEO_BUDGET,
                 min_interval: float = GEO_MIN_INTERVAL, enabled: bool = True):
        self.cache_file = cache_file
        self.budget_s = budget_s
        self.min_interval = min_interval
        self.enabled = enabled
        self.hosts = {}
        self.ips = {}
        self.dirty = False
        self._last_call = 0.0
        self._load()
        self.cf_nets = self._load_cloudflare_nets()

    def _load(self):
        p = Path(self.cache_file)
        if not p.exists():
            return
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("GeoIP cache unreadable (%s) - starting fresh", e)
            return
        if isinstance(raw, dict) and ("hosts" in raw or "ips" in raw):
            self.hosts = raw.get("hosts", {}) or {}
            self.ips = raw.get("ips", {}) or {}
        else:
            now = time.time()
            for ip, info in (raw or {}).items():
                if isinstance(info, dict):
                    self.ips[ip] = {**info, "t": now}
        logger.info("GeoIP cache loaded: %d hosts, %d IPs", len(self.hosts), len(self.ips))

    def save(self):
        try:
            Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"hosts": self.hosts, "ips": self.ips},
                          f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, self.cache_file)
            self.dirty = False
        except Exception as e:
            logger.warning("Error saving GeoIP cache: %s", e)

    def _load_cloudflare_nets(self):
        nets = []
        try:
            r = requests.get("https://www.cloudflare.com/ips-v4", timeout=8)
            if r.ok:
                nets = [ipaddress.ip_network(x.strip(), strict=False)
                        for x in r.text.split() if "/" in x]
        except Exception:
            pass
        if not nets:
            nets = [ipaddress.ip_network(c, strict=False) for c in CF_FALLBACK_CIDRS]
        return nets

    def is_cloudflare(self, ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in n for n in self.cf_nets)

    def resolve_many(self, hosts, deadline_s=DNS_DEADLINE):
        now = time.time()
        out, need = {}, []
        for h in hosts:
            if IPV4_RE.match(h):
                out[h] = h
                continue
            e = self.hosts.get(h)
            if e and (now - e.get("t", 0)) < HOST_TTL:
                out[h] = e.get("ip")
            else:
                need.append(h)

        if need:
            logger.info("DNS: %d hosts known from cache, resolving %d new ones...",
                        len(out), len(need))
            fresh = resolve_hosts(need, deadline_s=deadline_s)
            for h, ip in fresh.items():
                out[h] = ip
                self.hosts[h] = {"ip": ip, "t": now}
            self.dirty = True
        else:
            logger.info("DNS: all %d hosts served from cache", len(out))
        return out

    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def enrich(self, ips, batch_size=100, max_retries=3):
        if not self.enabled:
            logger.info("GeoIP disabled - skipping %d lookups", len(ips))
            return
        now = time.time()
        pending = []
        for ip in ips:
            if not ip:
                continue
            e = self.ips.get(ip)
            if e:
                age = now - e.get("t", 0)
                if e.get("neg") and age < GEO_NEG_TTL:
                    continue
                if not e.get("neg") and age < GEO_TTL:
                    continue
            pending.append(ip)
        if not pending:
            logger.info("GeoIP: all %d IPs served from cache", len(ips))
            return

        logger.info("GeoIP: %d/%d IPs need a lookup (%d cached). Budget %ds, ~%.1fs per batch.",
                    len(pending), len(ips), len(ips) - len(pending),
                    self.budget_s, self.min_interval)
        start = time.time()
        done = 0
        batch_size = min(100, max(1, batch_size))
        batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

        for idx, batch in enumerate(batches, 1):
            if time.time() - start > self.budget_s:
                logger.warning("GeoIP budget exhausted after %d/%d batches (%d IPs left unlabelled).",
                               idx - 1, len(batches), len(pending) - done)
                break
            for attempt in range(1, max_retries + 1):
                self._throttle()
                try:
                    resp = requests.post(
                        "http://ip-api.com/batch"
                        "?fields=status,country,countryCode,org,as,query",
                        json=batch, timeout=20)
                except Exception as e:
                    logger.warning("GeoIP request failed (%s) - retry %d/%d", e, attempt, max_retries)
                    time.sleep(2 * attempt)
                    continue

                if resp.status_code == 429:
                    ttl = int(resp.headers.get("X-Ttl", "60") or 60)
                    logger.info("GeoIP rate limited - sleeping %ds", ttl)
                    time.sleep(min(ttl, 65))
                    continue
                if resp.status_code != 200:
                    logger.warning("GeoIP HTTP %s - retry %d/%d", resp.status_code, attempt, max_retries)
                    time.sleep(2 * attempt)
                    continue

                try:
                    payload = resp.json()
                except Exception:
                    payload = []
                for item in payload:
                    q = item.get("query")
                    if not q:
                        continue
                    if item.get("status") != "success":
                        self.ips[q] = {"cc": "", "country": "", "org": "", "t": time.time(),
                                       "neg": True}
                        continue
                    org = (item.get("org") or item.get("as") or "").strip()
                    short = org.split()[1] if (org.upper().startswith("AS") and len(org.split()) > 1) else org
                    self.ips[q] = {
                        "cc": item.get("countryCode", ""),
                        "country": item.get("country", ""),
                        "org": (short or "Cloud")[:16],
                        "t": time.time(),
                    }
                done += len(batch)
                self.dirty = True
                rl = resp.headers.get("X-Rl")
                if rl is not None and rl.isdigit() and int(rl) <= 0:
                    ttl = int(resp.headers.get("X-Ttl", "60") or 60)
                    logger.info("GeoIP quota reached - pausing %ds", ttl)
                    time.sleep(min(ttl, 65))
                if idx % 20 == 0 or idx == len(batches):
                    logger.info("GeoIP progress: %d/%d batches, %.0fs elapsed",
                                idx, len(batches), time.time() - start)
                break

        cutoff = time.time() - GEO_TTL * 3
        self.ips = {k: v for k, v in self.ips.items() if v.get("t", 0) >= cutoff}
        self.hosts = {k: v for k, v in self.hosts.items()
                      if time.time() - v.get("t", 0) < HOST_TTL * 4}

    def get_info(self, ip: str, host: str):
        if (host.endswith(".pages.dev") or host.endswith(".workers.dev")
                or "cloudflare" in host):
            return "🌐", "اینترنت آزاد", "Cloudflare CDN", "global"
        if ip and IPV4_RE.match(ip) and self.is_cloudflare(ip):
            return "🌐", "اینترنت آزاد", "Cloudflare CDN", "global"

        info = self.ips.get(ip, {})
        cc = info.get("cc", "")
        if cc in COUNTRY_FA_MAP:
            flag, c_fa, slug = COUNTRY_FA_MAP[cc]
        elif cc:
            flag = country_code_to_flag(cc)
            c_fa = info.get("country", "اینترنت آزاد")
            slug = (info.get("country") or "global").lower().replace(" ", "_")
        else:
            flag, c_fa, slug = "🌐", "اینترنت آزاد", "global"
        return flag, c_fa, info.get("org", "Cloud Server"), slug


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


def build_5line_remark(flag, country_fa, dc, scheme, capability) -> str:
    return "\n".join([
        "👉🆔@Goodbaye_filtering",
        f"📡{flag} {country_fa}",
        f"®️{dc}",
        "🅿️ping:128ms",
        f"⚡{capability} | {scheme.upper()} IPv4",
    ])


def apply_goodbaye_remark(uri_clean: str, scheme: str, flag, c_fa, dc) -> str:
    capability = detect_capability(uri_clean, scheme)
    remark_text = build_5line_remark(flag, c_fa, dc, scheme, capability)

    if scheme == "vmess":
        payload = uri_clean.split("://", 1)[-1]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                data = json.loads(decoded)
                data["ps"] = remark_text
                blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                return "vmess://" + b64_encode_nopad(blob.encode("utf-8"))
            except Exception:
                pass
        return uri_clean
    return f"{uri_clean}#{quote(remark_text, safe='')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dns-workers", type=int, default=DNS_WORKERS)
    ap.add_argument("--dns-deadline", type=int, default=DNS_DEADLINE)
    ap.add_argument("--geo-budget", type=int, default=GEO_BUDGET)
    ap.add_argument("--geo-interval", type=float, default=GEO_MIN_INTERVAL)
    ap.add_argument("--no-geo", action="store_true", help="skip all GeoIP calls")
    args = ap.parse_args()

    t0 = time.time()
    if not os.path.exists(ALL_SERVERS):
        logger.error("%s not found!", ALL_SERVERS)
        return 1

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    logger.info("Loaded %d candidate servers. Starting strict unique filtering...",
                len(raw_lines))

    os.makedirs(SERVERS_DIR, exist_ok=True)
    os.makedirs(COUNTRIES_DIR, exist_ok=True)
    for old_f in Path(COUNTRIES_DIR).glob("*.txt"):
        try:
            old_f.unlink()
        except Exception:
            pass

    seen, unique_candidates, bad = set(), [], 0
    for cfg in raw_lines:
        if "://" not in cfg:
            bad += 1
            continue
        raw_scheme = cfg.split("://", 1)[0].strip().lower()
        proto = PROTO_MAP.get(raw_scheme, raw_scheme)
        clean_uri, host, port = extract_endpoint_signature(cfg, proto)
        if not host or port <= 0:
            bad += 1
            continue
        sig = (proto, host, port)
        if sig in seen:
            continue
        seen.add(sig)
        unique_candidates.append({"clean_uri": clean_uri, "raw_scheme": raw_scheme,
                                  "proto": proto, "host": host, "port": port})

    logger.info("Strict deduplication completed: %d unique endpoints (%d dropped as "
                "unparsable/duplicate).", len(unique_candidates), bad)

    geo = GeoIPManager(GEO_CACHE_FILE, budget_s=args.geo_budget,
                       min_interval=args.geo_interval, enabled=not args.no_geo)
    hosts = {c["host"] for c in unique_candidates}
    logger.info("Resolving %d unique hosts...", len(hosts))
    host_ip = geo.resolve_many(hosts, deadline_s=args.dns_deadline)
    logger.info("DNS phase done in %.0fs", time.time() - t0)

    ip_of = {c["host"]: (host_ip.get(c["host"]) or "") for c in unique_candidates}
    uniq_ips = {ip for ip in ip_of.values() if ip}
    geo.enrich(sorted(uniq_ips))
    geo.save()
    logger.info("GeoIP phase done (%d IPs labelled, %.0fs elapsed)",
                len(geo.ips), time.time() - t0)

    remarked_all, protocol_groups, country_groups = [], {}, {}
    for item in unique_candidates:
        clean_uri = item["clean_uri"]
        host, proto = item["host"], item["proto"]
        ip = ip_of[host]
        flag, c_fa, dc, slug = geo.get_info(ip, host)
        if item["raw_scheme"] != proto:
            clean_uri = clean_uri.replace(f"{item['raw_scheme']}://", f"{proto}://", 1)
        remarked = apply_goodbaye_remark(clean_uri, proto, flag, c_fa, dc)
        remarked_all.append(remarked)
        protocol_groups.setdefault(proto, []).append(remarked)
        country_groups.setdefault(slug, []).append(remarked)

    if remarked_all:
        with open(ALL_SERVERS, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(remarked_all) + "\n")
    logger.info("all_servers.txt updated: %d strictly unique configs.", len(remarked_all))

    for p, items in protocol_groups.items():
        with open(f"{SERVERS_DIR}/{p}_servers.txt", "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")

    written = 0
    for slug, items in country_groups.items():
        if slug == "global" and len(items) > 300:
            continue
        with open(f"{COUNTRIES_DIR}/{slug}.txt", "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(items) + "\n")
        written += 1

    logger.info("Successfully sharded %d country files in '%s'. Total runtime %.0fs.",
                written, COUNTRIES_DIR, time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
