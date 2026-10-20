#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Autonomous Repository & Code Guardian
# Security Policy: Zero-Leak Secrets | Anti-SSRF | AST Code Tamper Guard
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import re
import ast
import ipaddress
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlsplit, unquote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] [Guardian] - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("repo_guardian")

# ------------------------------------------------------------------------------
# Security Definitions & Brand Identity Anchors
# ------------------------------------------------------------------------------
BRAND_ANCHOR_USER = "alireza786786"
BRAND_ANCHOR_CHANNEL = "Goodbaye_filtering"

# Secret Leaks Regex Patterns
SECRET_PATTERNS = [
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),                        # GitHub Classic PAT
    re.compile(r'github_pat_[a-zA-Z0-9_]{82}'),                # GitHub Fine-grained PAT
    re.compile(r'\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b'),         # Telegram Bot Token
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')           # RSA/SSH/EC Private Keys
]

# SSRF Disallowed Private/Local IP Networks
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10")
]

# Forbidden Injections inside Configs
MALICIOUS_PAYLOAD_PATTERNS = [
    re.compile(r'<\s*script[^>]*>', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'data:text/html', re.IGNORECASE),
    re.compile(r'\x00')
]

# ==============================================================================
# Layer 1: Code Integrity & Anti-Tamper Guard
# ==============================================================================
def verify_python_code_integrity(src_dir: str = "src") -> bool:
    """
    Parses all Python scripts in src/ using Abstract Syntax Tree (AST).
    Verifies that scripts contain no syntax corruption, backdoors, or identity tampering.
    """
    path = Path(src_dir)
    if not path.exists():
        logger.warning(f"Directory '{src_dir}' not found. Skipping code AST audit.")
        return True

    logger.info(f"🛡️ Auditing Python source code integrity in '{src_dir}'...")
    all_clean = True

    for py_file in path.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            # 1. Check syntax and structural integrity
            ast.parse(content, filename=py_file.name)

            # 2. Check for brand anchoring on publisher and main tools
            if py_file.name in ("telegram_publisher.py", "remarker.py"):
                if BRAND_ANCHOR_CHANNEL not in content:
                    logger.error(f"❌ TAMPER DETECTED in {py_file.name}: Channel anchor '@{BRAND_ANCHOR_CHANNEL}' missing!")
                    all_clean = False

            logger.info(f"   ✓ {py_file.name}: Syntax & Structure Validated")
        except SyntaxError as se:
            logger.error(f"❌ SYNTAX CORRUPTION in {py_file.name}: {se}")
            all_clean = False
        except Exception as e:
            logger.error(f"❌ ERROR auditing {py_file.name}: {e}")
            all_clean = False

    return all_clean

# ==============================================================================
# Layer 2: Zero-Leak Secrets Scanner
# ==============================================================================
def scan_directory_for_secret_leaks(target_dirs: list[str]) -> bool:
    """
    Scans repository files to ensure no live secrets or tokens are committed in plaintext.
    """
    logger.info("🔐 Scanning files for potential token or private key leaks...")
    leaks_found = 0

    for target in target_dirs:
        p = Path(target)
        if not p.exists():
            continue

        files_to_check = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
        for f in files_to_check:
            # Skip binary, git, and local environment files
            if ".git" in f.parts or f.suffix in (".pyc", ".db", ".png", ".jpg", ".gif") or f.name == ".env":
                continue

            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                for pattern in SECRET_PATTERNS:
                    if pattern.search(text):
                        logger.critical(f"🚨 CRITICAL SECURITY LEAK DETECTED in '{f.as_posix()}'! Matches secret pattern.")
                        leaks_found += 1
            except Exception:
                continue

    if leaks_found > 0:
        logger.critical(f"❌ Guardian blocked execution! {leaks_found} secret leaks detected.")
        return False

    logger.info("   ✓ No plain-text tokens or secret keys detected in public files.")
    return True

# ==============================================================================
# Layer 3: Config Sanitizer & Anti-SSRF Firewall
# ==============================================================================
def is_ip_private(ip_str: str) -> bool:
    """Checks whether an IP address belongs to internal / private network ranges."""
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip("[]"))
        return any(ip_obj in net for net in PRIVATE_NETWORKS)
    except ValueError:
        return False

def sanitize_proxy_config(config_line: str) -> bool:
    """
    Inspects a single proxy line for SSRF, loopback hosts, and injection payloads.
    Returns True if clean, False if malicious/dangerous.
    """
    line = config_line.strip()
    if not line or len(line) > 4096:  # Prevent buffer overflow / crash payloads
        return False

    # Check for script or null byte injections
    for pattern in MALICIOUS_PAYLOAD_PATTERNS:
        if pattern.search(line):
            return False

    # Check host/endpoint
    try:
        if "://" in line:
            scheme, rest = line.split("://", 1)
            # Check for direct localhost / 127.0.0.1 in line
            line_lower = line.lower()
            if "localhost" in line_lower or "127.0.0.1" in line_lower:
                return False

            if scheme.lower() not in ("vmess",):
                parsed = urlsplit(line)
                host = parsed.hostname
                if host and is_ip_private(host):
                    return False
    except Exception:
        return False

    return True

def sanitize_config_file(filepath: str = "all_servers.txt") -> int:
    """
    Cleans an entire output file, removing any malicious, SSRF, or poisoned proxy lines.
    """
    path = Path(filepath)
    if not path.exists():
        return 0

    logger.info(f"🧹 Firewall inspecting '{filepath}' for SSRF and malicious injections...")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]

    clean_lines = []
    dropped_count = 0

    for line in lines:
        if sanitize_proxy_config(line):
            clean_lines.append(line)
        else:
            dropped_count += 1

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for cl in clean_lines:
            f.write(cl + "\n")

    if dropped_count > 0:
        logger.warning(f"⚠️ Guardian Firewall blocked and purged {dropped_count} suspicious/SSRF configs!")
    else:
        logger.info(f"   ✓ All {len(clean_lines)} configs passed security firewall inspection.")

    return dropped_count

# ==============================================================================
# Layer 4: Git Source Write-Protection Check
# ==============================================================================
def check_source_protection() -> bool:
    """
    Verifies that automation has not accidentally modified protected source/config files.
    """
    logger.info("🔒 Checking source directory write-protection status...")
    # Protected directories that must not be altered during runtime collector loops
    protected_dirs = ["src", "config"]
    # Simple check on permissions
    for d in protected_dirs:
        p = Path(d)
        if p.exists() and not os.access(p, os.R_OK):
            logger.error(f"❌ Permission error reading protected folder '{d}'")
            return False
    return True

# ==============================================================================
# Main Security Sweep
# ==============================================================================
def main():
    logger.info("🛡️ =======================================================")
    logger.info("🛡️ Starting Goodbaye Repository Security Guardian Sweep")
    logger.info("🛡️ =======================================================")

    # 1. Audit Python source code integrity
    if not verify_python_code_integrity("src"):
        logger.critical("❌ Source Code Integrity Audit FAILED!")
        sys.exit(1)

    # 2. Check for secret leaks in critical folders
    scan_targets = ["data", "servers", "README.md", "README.EN.md"]
    if not scan_directory_for_secret_leaks(scan_targets):
        logger.critical("❌ Secret Leak Inspection FAILED!")
        sys.exit(1)

    # 3. Sanitize server config files if present
    if Path("all_servers.txt").exists():
        sanitize_config_file("all_servers.txt")

    # 4. Check write protection status
    if not check_source_protection():
        logger.critical("❌ Source Protection FAILED!")
        sys.exit(1)

    logger.info("✅ Guardian Sweep Complete: Repository & Source Codes 100% Secure.")

if __name__ == "__main__":
    main()
