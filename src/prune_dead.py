#!/usr/bin/env python3
# ==============================================================================
# Dead-config pruner for Free-V2ray-Configs
# ==============================================================================

import os
import re
import sys
import json
import time
import base64
import socket
import queue
import random
import logging
import argparse
import threading
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prune_dead")

ALL_SERVERS = "all_servers.txt"
QUARANTINE = "data/quarantine.json"
GEO_CACHE = "data/geoip_cache.json"

IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
UDP_PROTOS = {"hysteria", "hysteria2", "hy2", "tuic", "juicity", "wireguard", "wg"}
CF_SUFFIXES = (".pages.dev", ".workers.dev", ".trycloudflare.com")

FAIL_LIMIT = 2
DECAY_DAYS = 7
PURGE_DAYS = 30
DNS_TTL = 3 * 86400

CF_FALLBACK_CIDRS = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]
CF_NETS = [ipaddress.ip_network(c, strict=False) for c in CF_FALLBACK_CIDRS]


def safe_b64_decode(text):
    s = text.strip().replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.b64decode(s).decode("utf-8", errors="ignore")
    except Exception:
        return ""


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


def endpoint(uri):
    clean = uri.split("#", 1)[0].strip()
    if "://" not in clean:
        return "", "", 0, clean
    raw = clean.split("://", 1)[0].strip().lower()
    proto = {"hy2": "hysteria2", "shadowsocks": "ss",
             "socks": "socks5", "socks4": "socks5"}.get(raw, raw)

    if proto == "vmess":
        payload = clean.split("://", 1)[1].split("?", 1)[0]
        decoded = safe_b64_decode(payload)
        if decoded:
            try:
                d = json.loads(decoded)
                h = str(d.get("add", "")).strip("[]").lower()
                try:
                    p = int(str(d.get("port", 0)).strip() or 0)
                except Exception:
                    p = 0
                return proto, h, p, clean
            except Exception:
                pass
        return proto, "", 0, clean

    if proto == "ss":
        part = clean.split("://", 1)[1].split("?", 1)[0]
        if "@" in part:
            _, hp = part.rsplit("@", 1)
            h, p = _split_host_port(hp)
        else:
            decoded = safe_b64_decode(part)
            h, p = ("", 0)
            if "@" in decoded:
                _, hp = decoded.rsplit("@", 1)
                h, p = _split_host_port(hp)
        return proto, h, p, clean

    try:
        u = urlsplit(clean)
        return proto, (u.hostname or "").strip("[]").lower(), (u.port or 0), clean
    except Exception:
        return proto, "", 0, clean


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def atomic_write_lines(path, lines):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def is_cf(host, ip):
    h = (host or "").lower()
    if h.endswith(CF_SUFFIXES) or "cloudflare" in h:
        return True
    if ip and IPV4_RE.match(ip):
        try:
            a = ipaddress.ip_address(ip)
            return any(a in n for n in CF_NETS)
        except ValueError:
            return False
    return False


def resolve_all(hosts, workers, deadline):
    out = {}
    q = queue.Queue()
    for h in hosts:
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
                out[h] = ip

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(min(workers, max(1, len(hosts))))]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=max(0.0, deadline - (time.time() - start)))
    with lock:
        for h in hosts:
            out.setdefault(h, None)
    ok = sum(1 for v in out.values() if v)
    logger.info("DNS: %d hosts, %d resolved (%.0fs)", len(hosts), ok, time.time() - start)
    return out


def tcp_ok(host, port, timeout):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def probe_many(items, workers, timeout):
    res = {}
    q = queue.Queue()
    for it in items:
        q.put(it)
    lock = threading.Lock()

    def worker():
        while True:
            try:
                key, host, port = q.get_nowait()
            except queue.Empty:
                return
            ok = tcp_ok(host, port, timeout)
            with lock:
                res[key] = ok

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(min(workers, max(1, len(items))))]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=max(5.0, (len(items) / max(1, workers)) * (timeout + 1) + 10))
    with lock:
        for key, _, _ in items:
            res.setdefault(key, None)
    alive = sum(1 for v in res.values() if v)
    logger.info("TCP: %d targets, %d reachable in %.0fs",
                len(items), alive, time.time() - start)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-check", type=int, default=25000)
    ap.add_argument("--workers", type=int, default=256)
    ap.add_argument("--timeout", type=float, default=3.5)
    ap.add_argument("--dns-deadline", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    if not os.path.exists(ALL_SERVERS):
        logger.error("%s not found", ALL_SERVERS)
        return 1

    with open(ALL_SERVERS, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip() and not ln.startswith("#")]

    logger.info("Loaded %d configs", len(lines))

    parsed = []
    for ln in lines:
        proto, host, port, clean = endpoint(ln)
        parsed.append({"line": ln, "proto": proto, "host": host, "port": port})

    quarantine = load_json(QUARANTINE, {}) or {}
    now = time.time()

    cache = load_json(GEO_CACHE, {}) or {}
    if not isinstance(cache, dict):
        cache = {}
    hosts_map = cache.get("hosts") or {}

    domains = {p["host"] for p in parsed
               if p["host"] and not IPV4_RE.match(p["host"])}
    fresh = [h for h in domains
             if not (hosts_map.get(h) and now - hosts_map[h].get("t", 0) < DNS_TTL)]
    if fresh:
        resolved = resolve_all(fresh, args.workers, args.dns_deadline)
        for h, ip in resolved.items():
            hosts_map[h] = {"ip": ip or "", "t": int(now)}
        cache["hosts"] = hosts_map
        save_json(GEO_CACHE, cache)
    else:
        logger.info("DNS: all %d domains already cached", len(domains))

    host_ip = {h: (hosts_map.get(h) or {}).get("ip", "") or "" for h in domains}

    candidates = []
    for p in parsed:
        if not p["host"] or p["port"] <= 0:
            continue
        if p["proto"] in UDP_PROTOS:
            continue
        ip = p["host"] if IPV4_RE.match(p["host"]) else host_ip.get(p["host"], "")
        if not ip:
            continue
        if is_cf(p["host"], ip):
            continue
        candidates.append((f'{p["proto"]}|{p["host"]}|{p["port"]}', ip, p["port"]))

    random.seed(int(now // 1800))
    random.shuffle(candidates)
    sample = candidates[:args.max_check]

    results = probe_many(sample, args.workers, args.timeout) if sample else {}

    def bump(key, failed):
        rec = quarantine.get(key)
        if failed:
            quarantine[key] = [(rec[0] if rec else 0) + 1, int(now)]
        elif rec:
            quarantine[key] = [0, int(now)]

    checked = 0
    for key, ok in results.items():
        if ok is None:
            continue
        checked += 1
        bump(key, not ok)

    for p in parsed:
        if not p["host"] or p["port"] <= 0 or p["proto"] in UDP_PROTOS:
            continue
        ip = p["host"] if IPV4_RE.match(p["host"]) else host_ip.get(p["host"], "")
        if ip:
            continue
        bump(f'{p["proto"]}|{p["host"]}|{p["port"]}', True)

    kept_q = {}
    for k, v in quarantine.items():
        age = now - v[1]
        if v[0] and age > DECAY_DAYS * 86400:
            continue
        if age > PURGE_DAYS * 86400:
            continue
        kept_q[k] = v
    quarantine = kept_q

    removed = 0
    kept = []
    for p in parsed:
        key = f'{p["proto"]}|{p["host"]}|{p["port"]}'
        rec = quarantine.get(key)
        if rec and rec[0] >= FAIL_LIMIT:
            removed += 1
            continue
        kept.append(p["line"])

    logger.info("Checked %d (TCP) | quarantined: %d | removed: %d (%d kept)",
                checked, len(quarantine), removed, len(kept))

    if args.dry_run:
        logger.info("dry-run: nothing written")
        return 0

    if kept:
        atomic_write_lines(ALL_SERVERS, kept)
    save_json(QUARANTINE, quarantine)
    logger.info("Done in %.0fs", time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
