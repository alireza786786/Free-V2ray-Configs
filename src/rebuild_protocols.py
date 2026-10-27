#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Protocol & Worldwide Country Rebuilder  (v4)
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os, re, sys, json, time, base64, socket, queue
import logging, threading, ipaddress, argparse
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

MMDB_COUNTRY = "data/GeoLite2-Country.mmdb"
MMDB_ASN = "data/GeoLite2-ASN.mmdb"
MMDB_BASE = "https://raw.githubusercontent.com/P3TERX/GeoLite.mmdb/download/"
MMDB_MAX_AGE = 7 * 86400

DNS_WORKERS = 128
DNS_DEADLINE = 150
GEO_BUDGET = 900
GEO_MIN_INTERVAL = 4.2
HOST_TTL = 7 * 86400
GEO_TTL = 60 * 86400
GEO_NEG_TTL = 3 * 86400

LITE_MAX = 150
EMERGENCY_MAX = 100
NO_CF_MAX = 15000

PROTO_MAP = {"hy2": "hysteria2", "vless": "vless", "shadowsocks": "ss",
             "socks": "socks5", "socks4": "socks5"}

COUNTRY_FA_MAP = {
    "JP": ("🇯🇵", "ژاپن", "japan"), "SE": ("🇸🇪", "سوئد", "sweden"),
    "US": ("🇺🇸", "آمریکا", "united_states"), "RU": ("🇷🇺", "روسیه", "russia"),
    "TR": ("🇹🇷", "ترکیه", "turkey"), "MY": ("🇲🇾", "مالزی", "malaysia"),
    "SG": ("🇸🇬", "سنگاپور", "singapore"), "DE": ("🇩🇪", "آلمان", "germany"),
    "NL": ("🇳🇱", "هلند", "netherlands"), "GB": ("🇬🇧", "انگلیس", "united_kingdom"),
    "FR": ("🇫🇷", "فرانسه", "france"), "FI": ("🇫🇮", "فنلاند", "finland"),
    "CA": ("🇨🇦", "کانادا", "canada"), "AE": ("🇦🇪", "امارات", "united_arab_emirates"),
    "IT": ("🇮🇹", "ایتالیا", "italy"), "ES": ("🇪🇸", "اسپانیا", "spain"),
    "PL": ("🇵🇱", "لهستان", "poland"), "CH": ("🇨🇭", "سوئیس", "switzerland"),
    "AT": ("🇦🇹", "اتریش", "austria"), "NO": ("🇳🇴", "نروژ", "norway"),
    "DK": ("🇩🇰", "دانمارک", "denmark"), "BE": ("🇧🇪", "بلژیک", "belgium"),
    "IR": ("🇮🇷", "ایران", "iran"), "UA": ("🇺🇦", "اوکراین", "ukraine"),
    "AU": ("🇦🇺", "استرالیا", "australia"), "IN": ("🇮🇳", "هند", "india"),
    "KR": ("🇰🇷", "کره جنوبی", "south_korea"), "HK": ("🇭🇰", "هنگ کنگ", "hong_kong"),
    "TW": ("🇹🇼", "تایوان", "taiwan"), "BR": ("🇧🇷", "برزیل", "brazil"),
    "ZA": ("🇿🇦", "آفریقای جنوبی", "south_africa"), "IE": ("🇮🇪", "ایرلند", "ireland"),
    "RO": ("🇷🇴", "رومانی", "romania"), "CZ": ("🇨🇿", "جمهوری چک", "czech_republic"),
}

IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

CF_FALLBACK_CIDRS = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]


def country_code_to_flag(code):
    if not code or len(code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c.upper())) for c in code)


def safe_b64_decode(text):
    s = text.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def b64_encode_nopad(data):
    return base64.b64encode(data).decode("utf-8").rstrip("=")


def atomic_write(path, lines):
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def _split_host_port(hp):
    hp = hp.strip()
    if hp.startswith("["):
        host, _, rest = hp[1:].partition("]")
        port = rest.lstrip(":")
        return host.lower(), (int(port) if port.isdigit() else 0)
    if hp.count(":") == 1:
        h, p = hp.rsplit(":", 1)
        return h.strip("[]").lower(), (int(p) if p.isdigit() else 0)
    return hp.strip("[]").lower(), 0


def extract_endpoint_signature(uri, scheme):
    clean_uri = uri.split("#", 1)[0].strip()
    host, port = "", 0

    if scheme == "vmess":
        payload = clean_uri.split("://", 1)[-1].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        data = None
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
            _, hp = part.rsplit("@", 1)
            host, port = _split_host_port(hp)
        else:
            decoded = safe_b64_decode(part)
            if "@" in decoded:
                _, hp = decoded.rsplit("@", 1)
                host, port = _split_host_port(hp)
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
    resolved, pending = {}, []
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

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(min(workers, len(pending)))]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=max(0.0, deadline_s - (time.time() - start)))

    missing = 0
    with lock:
        for h in pending:
            if h not in resolved:
                resolved[h] = None
                missing += 1

    ok = sum(1 for h in pending if resolved.get(h))
    logger.info("DNS: %d hostnames -> %d resolved, %d failed, %d skipped (%.1fs)",
                len(pending), ok, len(pending) - ok - missing, missing, time.time() - start)
    return resolved


class GeoIPManager:
    def __init__(self, cache_file, budget_s=GEO_BUDGET,
                 min_interval=GEO_MIN_INTERVAL, enabled=True):
        self.cache_file = cache_file
        self.budget_s = budget_s
        self.min_interval = min_interval
        self.enabled = enabled
        self.hosts, self.ips = {}, {}
        self._last_call = 0.0
        self._load()
        self.cf_nets = self._load_cloudflare_nets()
        self.mmdb_country, self.mmdb_asn = self._load_mmdb()

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
                    self.ips[ip] = dict(info, t=now)
        logger.info("GeoIP cache loaded: %d hosts, %d IPs", len(self.hosts), len(self.ips))

    def save(self):
        try:
            Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"hosts": self.hosts, "ips": self.ips},
                          f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, self.cache_file)
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
        return nets or [ipaddress.ip_network(c, strict=False) for c in CF_FALLBACK_CIDRS]

    def _load_mmdb(self):
        try:
            import maxminddb
        except Exception:
            logger.warning("maxminddb نصب نیست - استفاده از ip-api")
            return None, None
        readers = []
        for path, name in ((MMDB_COUNTRY, "GeoLite2-Country.mmdb"),
                           (MMDB_ASN, "GeoLite2-ASN.mmdb")):
            p = Path(path)
            try:
                if (not p.exists()) or (time.time() - p.stat().st_mtime > MMDB_MAX_AGE):
                    p.parent.mkdir(parents=True, exist_ok=True)
                    r = requests.get(MMDB_BASE + name, timeout=90)
                    if r.ok and len(r.content) > 500_000:
                        p.write_bytes(r.content)
                        logger.info("GeoIP DB: %s (%.1f MB)", name, len(r.content) / 1e6)
            except Exception as e:
                logger.warning("دانلود %s ناموفق: %s", name, e)
            try:
                readers.append(maxminddb.open_database(str(p)) if p.exists() else None)
            except Exception as e:
                logger.warning("باز کردن %s ناموفق: %s", name, e)
                readers.append(None)
        return readers[0], readers[1]

    def is_cloudflare(self, ip):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in n for n in self.cf_nets)

    def is_cf_host(self, ip, host):
        if (host.endswith(".pages.dev") or host.endswith(".workers.dev")
                or "cloudflare" in host):
            return True
        return bool(ip) and bool(IPV4_RE.match(ip)) and self.is_cloudflare(ip)

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
            logger.info("DNS: %d hosts from cache, resolving %d new...", len(out), len(need))
            for h, ip in resolve_hosts(need, deadline_s=deadline_s).items():
                out[h] = ip
                self.hosts[h] = {"ip": ip, "t": now}
        else:
            logger.info("DNS: all %d hosts served from cache", len(out))
        return out

    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def _offline(self, ips):
        now = time.time()
        added = 0
        for ip in ips:
            if not ip or ip in self.ips:
                continue
            try:
                rec = self.mmdb_country.get(ip) or {}
            except Exception:
                rec = {}
            cc = (rec.get("country") or {}).get("iso_code") or ""
            if not cc:
                self.ips[ip] = {"cc": "", "country": "", "org": "", "t": now, "neg": True}
                continue
            org = "Cloud"
            if self.mmdb_asn is not None:
                try:
                    org = ((self.mmdb_asn.get(ip) or {})
                           .get("autonomous_system_organization") or "Cloud")
                except Exception:
                    pass
            self.ips[ip] = {
                "cc": cc,
                "country": (rec.get("country") or {}).get("names", {}).get("en", cc),
                "org": org[:16], "t": now,
            }
            added += 1
        self.save()
        logger.info("GeoIP آفلاین: %d آی‌پی در لحظه لیبل شد", added)

    def enrich(self, ips, batch_size=100, max_retries=3):
        if not self.enabled:
            logger.info("GeoIP disabled - skipping %d lookups", len(ips))
            return
        if self.mmdb_country is not None:
            self._offline(ips)
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

        logger.info("GeoIP: %d/%d IPs need a lookup. Budget %ds.",
                    len(pending), len(ips), self.budget_s)
        start, done = time.time(), 0
        batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]

        for idx, batch in enumerate(batches, 1):
            if time.time() - start > self.budget_s:
                logger.warning("GeoIP budget exhausted after %d/%d batches.", idx - 1, len(batches))
                break
            for attempt in range(1, max_retries + 1):
                self._throttle()
                try:
                    resp = requests.post(
                        "http://ip-api.com/batch"
                        "?fields=status,country,countryCode,org,as,query",
                        json=batch, timeout=20)
                except Exception as e:
                    logger.warning("GeoIP request failed (%s) retry %d/%d", e, attempt, max_retries)
                    time.sleep(2 * attempt)
                    continue
                if resp.status_code == 429:
                    ttl = int(resp.headers.get("X-Ttl", "60") or 60)
                    logger.info("GeoIP rate limited - sleeping %ds", ttl)
                    time.sleep(min(ttl, 65))
                    continue
                if resp.status_code != 200:
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
                        self.ips[q] = {"cc": "", "country": "", "org": "",
                                       "t": time.time(), "neg": True}
                        continue
                    org = (item.get("org") or item.get("as") or "").strip()
                    short = (org.split()[1]
                             if org.upper().startswith("AS") and len(org.split()) > 1 else org)
                    self.ips[q] = {"cc": item.get("countryCode", ""),
                                   "country": item.get("country", ""),
                                   "org": (short or "Cloud")[:16], "t": time.time()}
                done += len(batch)
                rl = resp.headers.get("X-Rl")
                if rl and rl.isdigit() and int(rl) <= 0:
                    time.sleep(min(int(resp.headers.get("X-Ttl", "60") or 60), 65))
                if idx % 20 == 0 or idx == len(batches):
                    self.save()
                    logger.info("GeoIP progress: %d/%d batches, %.0fs",
                                idx, len(batches), time.time() - start)
                break

        cutoff = time.time() - GEO_TTL * 3
        self.ips = {k: v for k, v in self.ips.items() if v.get("t", 0) >= cutoff}
        self.hosts = {k: v for k, v in self.hosts.items()
                      if time.time() - v.get("t", 0) < HOST_TTL * 4}
        self.save()

    def get_info(self, ip, host):
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


def detect_capability(uri_clean, scheme):
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


def build_5line_remark(flag, country_fa, dc, scheme, capability):
    return "\n".join([
        "👉🆔@Goodbaye_filtering",
        f"📡{flag} {country_fa}",
        f"®️{dc}",
        "🅿️ping:128ms",
        f"⚡{capability} | {scheme.upper()} IPv4",
    ])


def apply_goodbaye_remark(uri_clean, scheme, flag, c_fa, dc):
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
    ap.add_argument("--no-geo", action="store_true")
    ap.add_argument("--max-per-proto", type=int, default=0)
    args = ap.parse_args()

    t0 = time.time()
    if not os.path.exists(ALL_SERVERS):
        logger.error("%s not found!", ALL_SERVERS)
        return 1

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    logger.info("Loaded %d candidate servers. Starting strict unique filtering...", len(raw_lines))

    os.makedirs(SERVERS_DIR, exist_ok=True)
    os.makedirs(COUNTRIES_DIR, exist_ok=True)
    for old in Path(COUNTRIES_DIR).glob("*.txt"):
        try:
            old.unlink()
        except Exception:
            pass

    removed = 0
    for stale in ("iran_fast.txt", "vless.txt", "vmess.txt", "trojan.txt",
                  "ss.txt", "hysteria2.txt", "tuic.txt", "socks.txt"):
        f = Path(SERVERS_DIR) / stale
        try:
            if f.exists():
                f.unlink()
                removed += 1
        except Exception:
            pass
    if removed:
        logger.info("Removed %d stale shards (~40MB freed).", removed)

    seen, unique_candidates, bad, per_proto = set(), [], 0, {}
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
        if args.max_per_proto and per_proto.get(proto, 0) >= args.max_per_proto:
            continue
        per_proto[proto] = per_proto.get(proto, 0) + 1
        seen.add(sig)
        unique_candidates.append({"clean_uri": clean_uri, "raw_scheme": raw_scheme,
                                  "proto": proto, "host": host, "port": port})

    logger.info("Strict deduplication completed: %d unique endpoints (%d dropped).",
                len(unique_candidates), bad)

    geo = GeoIPManager(GEO_CACHE_FILE, budget_s=args.geo_budget,
                       min_interval=args.geo_interval, enabled=not args.no_geo)
    hosts = {c["host"] for c in unique_candidates}
    logger.info("Resolving %d unique hosts...", len(hosts))
    host_ip = geo.resolve_many(hosts, deadline_s=args.dns_deadline)
    logger.info("DNS phase done in %.0fs", time.time() - t0)

    ip_of = {c["host"]: (host_ip.get(c["host"]) or "") for c in unique_candidates}
    geo.enrich(sorted({ip for ip in ip_of.values() if ip}))
    logger.info("GeoIP phase done (%d IPs labelled, %.0fs)", len(geo.ips), time.time() - t0)

    remarked_all, protocol_groups, country_groups = [], {}, {}
    no_cf, socks_emergency = [], []

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
        if not geo.is_cf_host(ip, host) and len(no_cf) < NO_CF_MAX:
            no_cf.append(remarked)
        if proto in ("socks5", "socks") and len(socks_emergency) < EMERGENCY_MAX:
            socks_emergency.append(remarked)

    if remarked_all:
        atomic_write(ALL_SERVERS, remarked_all)
    logger.info("all_servers.txt updated: %d configs.", len(remarked_all))

    for p, items in protocol_groups.items():
        atomic_write(f"{SERVERS_DIR}/{p}_servers.txt", items)

    written = 0
    for slug, items in country_groups.items():
        if slug == "global" and len(items) > 300:
            continue
        atomic_write(f"{COUNTRIES_DIR}/{slug}.txt", items)
        written += 1
    logger.info("Country shards: %d files.", written)

    atomic_write(f"{SERVERS_DIR}/no_cloudflare.txt", no_cf)
    atomic_write(f"{SERVERS_DIR}/emergency_socks5.txt", socks_emergency)

    lite, seen_c = [], set()
    for slug, items in country_groups.items():
        if slug == "global" or not items or slug in seen_c:
            continue
        seen_c.add(slug)
        lite.append(items[0])
        if len(lite) >= LITE_MAX:
            break
    atomic_write(f"{SERVERS_DIR}/lite.txt", lite)

    logger.info("Extra shards: no_cloudflare=%d, emergency_socks5=%d, lite=%d",
                len(no_cf), len(socks_emergency), len(lite))
    logger.info("Total runtime %.0fs.", time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
