#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - Split Joined Proxy Links
# Repository: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import re
import sys

# Comprehensive list of recognized proxy schemes
KNOWN_SCHEMES = [
    'vless', 'vmess', 'ss', 'shadowsocks', 'trojan',
    'tuic', 'juicity', 'ssr', 'socks', 'socks4', 'socks5',
    'hysteria', 'hysteria2', 'hy2', 'wireguard', 'anytls'
]

# Regex pattern targeting the start of any recognized scheme
PATTERN = re.compile(
    r'(?:' + '|'.join(re.escape(s) for s in KNOWN_SCHEMES) + r')://',
    re.IGNORECASE
)

def extract_proxy_links(line: str) -> list[str]:
    """Extract individual proxy links from a conjoined line."""
    links = []
    matches = list(PATTERN.finditer(line))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        link = line[start:end].strip()
        if link:
            links.append(link)
    return links

def main():
    if len(sys.argv) < 2:
        input_file = "all_servers.txt"
    else:
        input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"⚠️ File '{input_file}' not found. Skipping split.")
        sys.exit(0)

    output_file = f"{input_file}.tmp"
    extracted_links = []

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as infile:
        for line in infile:
            clean_line = line.strip()
            if not clean_line or clean_line.startswith('#'):
                continue
            links_in_line = extract_proxy_links(clean_line)
            extracted_links.extend(links_in_line)

    with open(output_file, 'w', encoding='utf-8', newline='\n') as outfile:
        for link in extracted_links:
            outfile.write(link + '\n')

    # Atomic file replacement
    os.replace(output_file, input_file)
    print(f"✅ Split completed. {len(extracted_links)} unique lines written to '{input_file}'")

if __name__ == "__main__":
    main()
