<!-- ============================================================================== -->
<!-- Goodbaye Universal Standard - Official Repository Documentation (README.EN.md) -->
<!-- Repository: https://github.com/alireza786786/Free-V2ray-Configs                -->
<!-- ============================================================================== -->

<div align="center">
  <!-- Official Repository Banner -->
  <img src="https://github.com/user-attachments/assets/59eb03f3-27ec-495a-af0d-459b1c26a54b" alt="Free-V2ray-Configs Banner" style="width: 100%; max-width: 950px; border-radius: 14px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
</div>

<div align="center" style="margin-bottom: 20px;">
  <!-- Language Switch -->
  <a href="https://github.com/alireza786786/Free-V2ray-Configs/blob/main/README.md">
    <img src="https://img.shields.io/badge/Read_in-Farsi-FF5722?style=for-the-badge&logo=readthedocs" alt="Read in Farsi">
  </a>
</div>

<div align="center" style="margin-bottom: 15px;">
  <!-- Badges Row -->
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge&logo=open-source-initiative" alt="License">
  <img src="https://img.shields.io/badge/Latency-Strict_%3C500ms-red?style=for-the-badge&logo=speedtest&logoColor=white" alt="Ping Strict">
  <a href="https://t.me/Goodbaye_filtering" target="_blank">
    <img src="https://img.shields.io/badge/Telegram-Main_Channel-2CA5E0?style=for-the-badge&logo=telegram" alt="Telegram Main">
  </a>
  <a href="https://t.me/CONFIG_V2RAY_VIP" target="_blank">
    <img src="https://img.shields.io/badge/VIP-Discussion_Group-F59E0B?style=for-the-badge&logo=telegram" alt="Telegram VIP">
  </a>
  <a href="https://alireza786786.github.io/Free-V2ray-Configs/" target="_blank">
    <img src="https://img.shields.io/badge/Web_Panel-Online-10B981?style=for-the-badge&logo=google-chrome" alt="Web Panel">
  </a>
</div>

<div align="center" style="margin-bottom: 20px;">
  <img src="https://github.com/alireza786786/Free-V2ray-Configs/actions/workflows/collector.yml/badge.svg" alt="Collector Status">
</div>

# 🚀 V2Ray Config Collector — Free Automated Proxy Subscription
### 🛡️ Goodbaye Universal Quality Standard

> **یک گردآورنده‌ی هوشمند، بدون وابستگی و فوق‌العاده بهینه برای جمع‌آوری خودکار کانفیگ‌های V2Ray و پروتکل‌های مشابه.**  
> _An intelligent, dependency-free, and highly optimized collector for automated harvesting of V2Ray configs and similar protocols._

<p align="center">
This project leverages <strong>GitHub repositories</strong> and <strong>public Telegram channels</strong> simultaneously (without requiring any Telegram API token, bot session, or phone number) to provide the most powerful source of live, tested configs. All pipelines run <strong>fully automatically</strong> on GitHub Actions under a <strong>strict quality standard (real latency under 500ms)</strong>.
</p>

<img src="https://github.com/user-attachments/assets/10f7cba4-523a-4dd2-a6b3-e7eaba3e8ecf" alt="separator" style="display: block; margin: 30px auto;" />

## ✨ Distinctive Features

<table>
<thead>
<tr><th>Feature</th><th>Description</th></tr>
</thead>
<tbody>
<tr>
    <td><strong>🎯 Dual Harvesting (GitHub + Telegram)</strong></td>
    <td>Asynchronous crawling of GitHub repositories and Telegram web previews (<code>t.me/s</code>) without Telegram API or phone number dependencies, storing deduplicated nodes in SQLite.</td>
</tr>
<tr>
    <td><strong>⚡ Strict Latency Probe (Ping &lt; 500ms)</strong></td>
    <td>High-speed asynchronous TCP socket handshakes test real response times; dead, timed-out, or high-latency (&ge; 500ms) servers are instantly purged.</td>
</tr>
<tr>
    <td><strong>🌍 100% Free GeoIP &amp; Flag Resolution</strong></td>
    <td>Dynamic conversion of ISO country codes into Unicode flag emojis (🇩🇪, 🇫🇮, 🇺🇸, 🇳🇱, etc.) and datacenter identification (Cloudflare, Hetzner, OVH, etc.) with zero paid API costs.</td>
</tr>
<tr>
    <td><strong>🏷️ Official 5-Line Goodbaye Remark</strong></td>
    <td>Enforces the mandatory 5-line remark pattern across all protocols (including VMess JSON rewriting) with clean URL-encoding for client compatibility.</td>
</tr>
<tr>
    <td><strong>🌐 Online Web Panel (GitHub Pages)</strong></td>
    <td>Dedicated dark-themed web panel featuring dynamic QR codes, ISP smart filtering (MCI, Irancell, Wi-Fi), and one-click subscription copy buttons.</td>
</tr>
<tr>
    <td><strong>🛡️ Security Sentinel &amp; Anti-Poisoning</strong></td>
    <td>Internal firewall blocking SSRF, loopback, and private LAN IP injections, backed by pre-commit secret leak scanners and code integrity verifiers.</td>
</tr>
<tr>
    <td><strong>🔎 Autonomous Source Discovery</strong></td>
    <td>Constantly hunts for newly created GitHub proxy repos and active Telegram channels, expanding the database automatically over time.</td>
</tr>
<tr>
    <td><strong>📢 Automated Telegram Broadcasting</strong></td>
    <td>Directly publishes verified subscription files to the main channel with 4 official inline glass buttons and Persian Jalali date captions.</td>
</tr>
</tbody>
</table>

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 🏷️ The 5-Line Remark Standard (Principle 1)

Every config published by this repository strictly complies with this 5-line remark standard:

```text
👉🆔@Goodbaye_filtering
📡[Country Flag] [Country Name]
®️[City or Datacenter]
🅿️ping:[Real Latency]ms
⚡[True Capability] | [Protocol and IP Version]
```

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 📁 Live Subscription Files & Direct Links

All files are continuously refreshed and can be directly imported into **v2rayNG, v2rayN, Hiddify, Sing-box, Nekobox**, and **Clash**:

| Subscription Package | Filename | Description | Direct Link |
| :--- | :--- | :--- | :--- |
| **All Servers** | `all_servers.txt` | Complete verified collection (Ping < 500ms) | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/all_servers.txt) |
| **Ultra-Fast Lite** | `servers/lite.txt` | Top lowest-ping configs curated for gaming & streaming | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/lite.txt) |
| **No-Cloudflare** | `servers/no_cloudflare.txt` | Independent servers bypassing Cloudflare network blocks | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/no_cloudflare.txt) |
| **Emergency SOCKS5** | `servers/emergency_socks5.txt` | Direct SOCKS5 proxies for instant messaging connection | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/emergency_socks5.txt) |
| **VLESS Sub** | `servers/vless.txt` | Dedicated VLESS & Reality configurations | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/vless.txt) |
| **VMess Sub** | `servers/vmess.txt` | Stable VMess servers with official 5-line remark | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/vmess.txt) |
| **Trojan Sub** | `servers/trojan.txt` | High-security Trojan protocol nodes | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/trojan.txt) |
| **Shadowsocks Sub** | `servers/ss.txt` | Lightweight Shadowsocks servers | [Direct Download](https://alireza786786.github.io/Free-V2ray-Configs/servers/ss.txt) |

> 🌐 **Interactive Web Panel with Dynamic QR Codes:** [Goodbaye Online Web Panel](https://alireza786786.github.io/Free-V2ray-Configs/)

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 🗂️ Project Directory Tree

```text
.
├── .github/
│   └── workflows/
│       ├── collector.yml              # Primary CI/CD Pipeline (Dual-Token + Test + Publish)
│       └── cleaner_temp.yml           # Periodic Telegram channel validation workflow
│
├── config/
│   ├── requirements.txt               # Dependencies (Async stack + Jalali Calendar)
│   ├── .gitignore                     # Security exclusions (Secrets & Caches)
│   └── .env.example                   # Environment variable template
│
├── src/
│   ├── collector_git.py               # Optimized GitHub repository crawler
│   ├── telegram_collector.py          # Web-based Telegram scraper (No-API)
│   ├── split_links.py                 # Conjoined proxy link separator
│   ├── dedup_configs.py               # Protocol-aware semantic deduplicator
│   ├── checker.py                     # Real Latency Probe (<500ms) & GeoIP Resolver
│   ├── remarker.py                    # Official 5-line Goodbaye remark engine
│   ├── sharder.py                     # Package sharder & web panel statistics generator
│   ├── telegram_publisher.py          # Telegram broadcaster (4 glass buttons & Jalali caption)
│   ├── source_discovery.py            # Autonomous repo & channel hunter
│   ├── repo_guardian.py               # Repository sentinel, anti-SSRF & code protector
│   └── channel_cleaner.py             # Channel health tester
│
├── data/                              # Databases and runtime states
│   ├── channels.txt                   # Active target Telegram channels
│   ├── checkpoint.json                # Progress persistence across stops
│   ├── discovered_branches.json       # Learned GitHub default branches
│   └── token_state.txt                # Dual-token rotation counter
│
├── servers/                           # Sharded subscription outputs
│   ├── lite.txt                       # High-speed low-ping package
│   ├── no_cloudflare.txt              # Cloudflare-independent package
│   ├── emergency_socks5.txt           # Emergency SOCKS5 proxies
│   └── [protocol].txt                 # Protocol-specific files
│
├── for Developers/                    # Exhaustive developer databases
│   ├── collector_git_Fullversion.py   # Raw exhaustive GitHub collector
│   └── channels_Fullversion.txt       # Master database of 1500+ Telegram channels
│
├── banner.jpg                         # Official repository banner image
├── index.html                         # Interactive GitHub Pages Web Panel with QR Codes
├── all_servers.txt                    # Comprehensive master collection of live servers
├── line.gif                           # Animated visual divider
├── README.md                          # Official Persian documentation
└── README.EN.md                       # Official English documentation
```

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 🔐 GitHub Secrets Configuration

To run the continuous automated pipeline without rate-limiting, add these variables under **Settings > Secrets and variables > Actions**:

* `GH_TOKEN` : Personal Access Token (Classic) with `repo` and `workflow` scopes.
* `BOT_TOKEN` : Telegram Bot Token from [@BotFather](https://t.me/BotFather).
* `TARGET_CHAT_ID` : Destination Telegram channel username (`@Goodbaye_filtering`).
* *(Optional)* `GH_APP_ID` & `GH_APP_PRIVATE_KEY` : For secondary GitHub App token rotation to ensure unlimited API calls.

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 📢 Official Channels & Community

* **Main Broadcast Channel:** [@Goodbaye_filtering](https://t.me/Goodbaye_filtering)
* **VIP Discussion & Chat Group:** [@CONFIG_V2RAY_VIP](https://t.me/CONFIG_V2RAY_VIP)
* **Online Web Panel:** [https://alireza786786.github.io/Free-V2ray-Configs/](https://alireza786786.github.io/Free-V2ray-Configs/)

<img src="line.gif" alt="separator" style="display: block; margin: 30px auto;" />

## 📄 License
This repository is released under the **MIT** license. Free for use, modification, and community distribution to ensure free and uncensored internet access for all.
