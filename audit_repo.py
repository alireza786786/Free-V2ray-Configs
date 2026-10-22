#!/usr/bin/env python3
# ==============================================================================
# Goodbaye Universal Standard - 22-Point Repository Auditor Agent (Termux/CLI)
# Target: https://github.com/alireza786786/Free-V2ray-Configs
# ==============================================================================

import os
import sys
import json
import re
import urllib.request
from pathlib import Path

# ANSI Terminal Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_OWNER = "alireza786786"
REPO_NAME = "Free-V2ray-Configs"
PAGES_URL = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/"

def print_result(num: int, title: str, passed: bool, detail: str = ""):
    status = f"{GREEN}[✅ حل شده]{RESET}" if passed else f"{RED}[❌ هنوز حل نشده]{RESET}"
    print(f"{BOLD}{num:2d}. {title}{RESET}")
    print(f"    ↳ وضعیت: {status} {detail}")

def check_http_status(url: str) -> int:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0

def main():
    print(f"\n{CYAN}{BOLD}===================================================================={RESET}")
    print(f"{CYAN}{BOLD}🔎 شروع ارزیابی خودکار ۲۲ موردی مخزن {REPO_NAME}{RESET}")
    print(f"{CYAN}{BOLD}===================================================================={RESET}\n")

    # -------------------------------------------------------------------------
    # گروه الف: بلاکرهای راه‌اندازی و دیتا
    # -------------------------------------------------------------------------
    # ۱. فعال بودن collector.yml
    collector_yml = Path(".github/workflows/collector.yml")
    has_collector = collector_yml.exists()
    print_result(1, "وجود و ساختار collector.yml", has_collector,
                 f"({collector_yml.as_posix()})" if has_collector else "فایل یافت نشد")

    # ۲. اسکوپ توکن و گیت‌هاب اکشنز (بررسی مرحله ۱۸ در ورک‌فلو)
    has_self_trigger = False
    if has_collector:
        txt = collector_yml.read_text(encoding="utf-8", errors="ignore")
        has_self_trigger = "createWorkflowDispatch" in txt
    print_result(2, "پیکربندی تریگر خودکار (Self-Trigger)", has_self_trigger,
                 "نیازمند اسکوپ repo+workflow در GH_TOKEN" if has_self_trigger else "")

    # ۳. data/channels.txt
    ch_file = Path("data/channels.txt")
    has_channels = ch_file.exists() and ch_file.stat().st_size > 0
    ch_count = 0
    if has_channels:
        ch_count = len([l for l in ch_file.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and not l.startswith("#")])
    print_result(3, "وجود data/channels.txt", has_channels and ch_count > 0,
                 f"(تعداد: {ch_count} کانال)" if has_channels else "فایل وجود ندارد یا خالی است")

    # ۴. data/last_message_id.json
    lmid_file = Path("data/last_message_id.json")
    has_lmid = lmid_file.exists() and lmid_file.stat().st_size > 10
    print_result(4, "وجود data/last_message_id.json", has_lmid,
                 f"(حجم: {lmid_file.stat().st_size if has_lmid else 0} بایت)")

    # ۵. data/invalid_channels.txt و data/channel_report.txt
    has_reports = Path("data/invalid_channels.txt").exists() or Path("data/channel_report.txt").exists()
    print_result(5, "فایل‌های لاگ کانال‌ها در data/", has_reports,
                 "توسط channel_cleaner یا collector ساخته می‌شوند")

    # -------------------------------------------------------------------------
    # گروه ب: حجم، دیتابیس و پاکسازی
    # -------------------------------------------------------------------------
    # ۶. بررسی finalize_output (عدم انباشت ۱۰۰ هزارتایی)
    git_collector = Path("src/collector_git.py")
    uses_delta = False
    if git_collector.exists():
        txt = git_collector.read_text(encoding="utf-8", errors="ignore")
        if "all_combined" not in txt and "added_configs" in txt:
            uses_delta = True
    
    all_srv = Path("all_servers.txt")
    srv_size_mb = (all_srv.stat().st_size / (1024 * 1024)) if all_srv.exists() else 0
    print_result(6, "منطق خروجی دلتا (جلوگیری از انباشت ۱۰۰ هزارتایی)", uses_delta or srv_size_mb < 2.0,
                 f"(حجم فعلی all_servers: {srv_size_mb:.2f} MB)")

    # ۷. بررسی .gitignore برای فایل‌های حجیم JSON
    gitignore = Path("config/.gitignore")
    if not gitignore.exists():
        gitignore = Path(".gitignore")
    ignores_large = False
    if gitignore.exists():
        txt = gitignore.read_text(encoding="utf-8", errors="ignore")
        ignores_large = "tested_servers.json" in txt or "*.json" in txt
    print_result(7, "محافظت .gitignore از فایل‌های سنگین JSON", ignores_large)

    # ۸. سقف تست در checker.py
    checker_py = Path("src/checker.py")
    has_bounded_checker = False
    if checker_py.exists():
        txt = checker_py.read_text(encoding="utf-8", errors="ignore")
        has_bounded_checker = "MAX_PING_THRESHOLD_MS" in txt
    print_result(8, "فیلتر سرعت و پینگ در checker.py", has_bounded_checker)

    # ۹. تداخل اسامی کشورها (turkey.txt vs türkiye.txt)
    countries_dir = Path("servers/countries")
    has_country_conflict = False
    if countries_dir.exists():
        files = [f.name.lower() for f in countries_dir.glob("*.txt")]
        has_country_conflict = "turkey.txt" in files and "türkiye.txt" in files
    print_result(9, "عدم تداخل اسامی تکراری کشورها", not has_country_conflict)

    # -------------------------------------------------------------------------
    # گروه ج: الگوی ریمارک ۵ خطی و ساب‌ها
    # -------------------------------------------------------------------------
    # ۱۰. ریمارک ۵ خطی در servers/vless.txt و سایرین
    vless_file = Path("servers/vless.txt")
    has_vless_remark = False
    if vless_file.exists():
        txt = vless_file.read_text(encoding="utf-8", errors="ignore")
        has_vless_remark = "Goodbaye" in txt or "%40Goodbaye" in txt
    print_result(10, "اعمال ریمارک ۵ خطی در servers/vless.txt", has_vless_remark)

    # ۱۱. ریمارک ۵ خطی در servers/lite.txt
    lite_file = Path("servers/lite.txt")
    has_lite_remark = False
    if lite_file.exists():
        txt = lite_file.read_text(encoding="utf-8", errors="ignore")
        has_lite_remark = "Goodbaye" in txt or "%40Goodbaye" in txt
    print_result(11, "اعمال ریمارک ۵ خطی در servers/lite.txt", has_lite_remark)

    # ۱۲. تعارض مالکیت all_servers.txt بین remarker و sharder
    sharder_py = Path("src/sharder.py")
    sharder_conflicts = False
    if sharder_py.exists():
        txt = sharder_py.read_text(encoding="utf-8", errors="ignore")
        sharder_conflicts = 'open("all_servers.txt", "w"' in txt
    print_result(12, "تفکیک وظایف remarker و sharder روی all_servers", not sharder_conflicts)

    # ۱۳. عدم حذف ریمارک نهایی در dedup_configs.py
    dedup_py = Path("src/dedup_configs.py")
    has_dedup = dedup_py.exists()
    print_result(13, "وجود موتور پالایش سمانتیک dedup_configs", has_dedup)

    # -------------------------------------------------------------------------
    # گروه د: وب‌پنل و گیت‌هاب پیجز
    # -------------------------------------------------------------------------
    # ۱۴. تست زنده آنلاین بودن GitHub Pages
    pages_code = check_http_status(PAGES_URL)
    pages_online = pages_code == 200
    print_result(14, "آنلاین بودن GitHub Pages (کد HTTP)", pages_online,
                 f"(کد وضعیت: {pages_code}) -> {PAGES_URL}")

    # ۱۵. وجود فایل .nojekyll
    nojekyll = Path(".nojekyll")
    print_result(15, "وجود فایل خالی .nojekyll در ریشه", nojekyll.exists())

    # ۱۶. حجم کلی پوشه مخزن
    total_size_mb = sum(f.stat().st_size for f in Path(".").rglob("*") if f.is_file() and ".git" not in f.parts) / (1024 * 1024)
    print_result(16, "سبک بودن حجم کل مخزن (زیر ۲۰ مگابایت)", total_size_mb < 20,
                 f"(حجم کل سورس‌ها: {total_size_mb:.2f} MB)")

    # -------------------------------------------------------------------------
    # گروه ه: معماری و خط لوله
    # -------------------------------------------------------------------------
    # ۱۷. تنظیم تریگر cron و خودکار در collector.yml
    has_single_trigger = False
    if has_collector:
        txt = collector_yml.read_text(encoding="utf-8", errors="ignore")
        has_single_trigger = "workflow_dispatch:" in txt
    print_result(17, "پیکربندی تریگرهای collector.yml", has_single_trigger)

    # ۱۸. وجود src/rebuild_protocols.py
    rebuild_py = Path("src/rebuild_protocols.py")
    print_result(18, "وجود ماژول تفکیک پروتکل‌ها (rebuild_protocols)", rebuild_py.exists())

    # ۱۹. اجرای بدون بازنویسی مخرب در ددوپ
    dedup_safe = True
    if has_collector:
        txt = collector_yml.read_text(encoding="utf-8", errors="ignore")
        # اگر ددوپ قبل از ریمارکر اجرا شود امن است
        dedup_pos = txt.find("dedup_configs.py")
        remark_pos = txt.find("remarker.py")
        if dedup_pos != -1 and remark_pos != -1:
            dedup_safe = dedup_pos < remark_pos
    print_result(19, "ترتیب اجرای امن (Dedup قبل از Remarker)", dedup_safe)

    # ۲۰. بررسی اجرای source_discovery در ورک‌فلو یا پروژه
    disc_py = Path("src/source_discovery.py")
    print_result(20, "وجود ماژول کشف خودکار سورس‌ها (source_discovery)", disc_py.exists())

    # ۲۱. بررسی سلامت هدر repo_report.txt
    repo_rep = Path("data/repo_report.txt")
    rep_clean = True
    if repo_rep.exists():
        txt = repo_rep.read_text(encoding="utf-8", errors="ignore")
        rep_clean = "GitHub Repo Report — last update: 0, 0" not in txt
    print_result(21, "عدم تداخل هدر در repo_report.txt", rep_clean)

    # ۲۲. نسخه پایتون سازگار
    print_result(22, "نسخه پایتون رانر (سازگار با ۳.۱۰ تا ۳.۱۲)", sys.version_info >= (3, 10),
                 f"(نسخه فعلی شما: {sys.version.split()[0]})")

    print(f"\n{CYAN}{BOLD}===================================================================={RESET}")
    print(f"{BOLD}ارزیابی کامل شد. مواردی که علامت ❌ دارند اولویت اصلاح هستند.{RESET}\n")

if __name__ == "__main__":
    main()
