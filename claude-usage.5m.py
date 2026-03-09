#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <bitbar.title>Claude Fuel Gauge</bitbar.title>
# <bitbar.desc>Claude残量メーター - プラン使用量をメニューバーにリアルタイム表示</bitbar.desc>
# <bitbar.author>Kaz</bitbar.author>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CACHE_FILE = Path.home() / ".claude-usage-cache.json"
CLAUDE_JSON = Path.home() / ".claude.json"


def get_org_id():
    """Get organization UUID from ~/.claude.json"""
    try:
        with open(CLAUDE_JSON) as f:
            data = json.load(f)
        return data.get("oauthAccount", {}).get("organizationUuid")
    except Exception:
        return None


def is_chrome_running():
    """Check if Chrome is running without activating it."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "Google Chrome"],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


def fetch_usage_via_chrome(org_id):
    """Fetch usage data via synchronous XMLHttpRequest in an existing Claude.ai Chrome tab.
    Requires: Chrome > View > Developer > Allow JavaScript from Apple Events
    """
    if not is_chrome_running():
        return {"error": "chrome_not_running"}

    api_path = f"/api/organizations/{org_id}/usage"

    applescript = f'''
        tell application "Google Chrome"
            set windowList to every window
            repeat with w in windowList
                set tabList to every tab of w
                repeat with t in tabList
                    if URL of t contains "claude.ai" then
                        set result to execute t javascript "var xhr = new XMLHttpRequest(); xhr.open('GET', '{api_path}', false); xhr.send(); xhr.responseText"
                        return result
                    end if
                end repeat
            end repeat
            return "{{\\"error\\": \\"no_claude_tab\\"}}"
        end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "JavaScript" in stderr and ("オフ" in stderr or "off" in stderr.lower()):
                return {"error": "applescript_js_disabled"}
            return {"error": f"osascript_failed: {stderr[:100]}"}
        output = result.stdout.strip()
        if not output:
            return {"error": "empty_response"}
        return json.loads(output)
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except json.JSONDecodeError:
        return {"error": f"json_parse_error: {result.stdout.strip()[:80]}"}
    except Exception as e:
        return {"error": str(e)}


def save_cache(data):
    """Save usage data to cache file."""
    data["_cached_at"] = datetime.now(timezone.utc).isoformat()
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_cache():
    """Load cached usage data."""
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def format_reset_time(resets_at_str):
    """Format reset time as absolute day + time in Japanese."""
    try:
        resets_at = datetime.fromisoformat(resets_at_str)
        local_time = resets_at.astimezone()
        now = datetime.now().astimezone()

        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        day_name = weekdays[local_time.weekday()]
        time_str = local_time.strftime("%-H:%M")

        delta = resets_at - now.astimezone(resets_at.tzinfo)
        if delta.total_seconds() <= 0:
            return "まもなく"

        if local_time.date() == now.date():
            return f"今日 {time_str}"
        elif local_time.date() == (now + timedelta(days=1)).date():
            return f"明日 {time_str}"
        else:
            return f"{day_name} {time_str}"
    except Exception:
        return "不明"


def get_bar_color(pct):
    """Return color based on usage percentage."""
    if pct >= 80:
        return "#ff5555"
    if pct >= 60:
        return "#ffaa33"
    if pct >= 40:
        return "#ffdd44"
    return "#55cc55"


def get_fuel_emoji(pct):
    """Return emoji based on usage level."""
    if pct >= 80:
        return "🔴"
    if pct >= 60:
        return "🟠"
    if pct >= 40:
        return "🟡"
    return "🟢"


def make_bar(pct, width=10):
    """Create a text progress bar."""
    filled = round(pct / 100 * width)
    empty = width - filled
    return "▓" * filled + "░" * empty


def render_output(data, from_cache=False):
    """Render SwiftBar output."""
    five_hour = data.get("five_hour") or {}
    seven_day = data.get("seven_day") or {}
    seven_day_sonnet = data.get("seven_day_sonnet") or {}

    s_pct = five_hour.get("utilization", "?")
    w_pct = seven_day.get("utilization", "?")
    sn_pct = seven_day_sonnet.get("utilization", "?")

    # Convert float to int for cleaner display (60.0 -> 60)
    if isinstance(s_pct, float):
        s_pct = int(s_pct)
    if isinstance(w_pct, float):
        w_pct = int(w_pct)
    if isinstance(sn_pct, float):
        sn_pct = int(sn_pct)

    # Menu bar text - compact display
    s_val = s_pct if isinstance(s_pct, (int, float)) else 0
    w_val = w_pct if isinstance(w_pct, (int, float)) else 0

    # Title bar - compact with emoji indicator
    cache_mark = " *" if from_cache else ""
    worst = max(s_val, w_val)
    title_emoji = get_fuel_emoji(worst)
    print(f"{title_emoji} S:{s_pct}% W:{w_pct}%{cache_mark} | size=12")
    print("---")

    USAGE_URL = "href=https://claude.ai/settings/usage"

    # Session usage
    s_reset = format_reset_time(five_hour.get("resets_at", "")) if five_hour.get("resets_at") else "不明"
    s_emoji = get_fuel_emoji(s_val)
    s_bar = make_bar(s_val)
    s_color = get_bar_color(s_val)
    print(f"{s_emoji} セッション (5h): {s_pct}% | size=14 color={s_color} {USAGE_URL}")
    print(f"  {s_bar}  {s_reset} | size=12 font=Menlo {USAGE_URL}")
    print("---")

    # Weekly - all models
    w_reset = format_reset_time(seven_day.get("resets_at", "")) if seven_day.get("resets_at") else "不明"
    w_emoji = get_fuel_emoji(w_val)
    w_bar = make_bar(w_val)
    w_color = get_bar_color(w_val)
    print(f"{w_emoji} 週間 全モデル: {w_pct}% | size=14 color={w_color} {USAGE_URL}")
    print(f"  {w_bar}  {w_reset} | size=12 font=Menlo {USAGE_URL}")
    print("---")

    # Weekly - Sonnet
    if seven_day_sonnet.get("utilization") is not None:
        sn_val = sn_pct if isinstance(sn_pct, (int, float)) else 0
        sn_reset = format_reset_time(seven_day_sonnet.get("resets_at", "")) if seven_day_sonnet.get("resets_at") else "不明"
        sn_emoji = get_fuel_emoji(sn_val)
        sn_bar = make_bar(sn_val)
        sn_color = get_bar_color(sn_val)
        print(f"{sn_emoji} 週間 Sonnet: {sn_pct}% | size=14 color={sn_color} {USAGE_URL}")
        print(f"  {sn_bar}  {sn_reset} | size=12 font=Menlo {USAGE_URL}")
        print("---")

    # Cache info
    cached_at = data.get("_cached_at", "")
    if cached_at:
        cache_label = format_reset_time_ago(cached_at)
        marker = " (キャッシュ)" if from_cache else ""
        print(f"⏱ 更新: {cache_label}{marker} | size=11 refresh=true")
    print("---")

    # Refresh & link
    print("🔄 今すぐ更新 | refresh=true")
    print("---")
    print("📊 claude.ai/settings/usage を開く | href=https://claude.ai/settings/usage")
    print("---")
    print("⏻ 終了 (watchdogも停止) | bash=/bin/sh param1=-c param2=launchctl\\ unload\\ ~/Library/LaunchAgents/com.swiftbar.watchdog.plist\\ 2>/dev/null\\;\\ killall\\ SwiftBar terminal=false")


def format_reset_time_ago(iso_str):
    """Format a past time as relative time."""
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        delta = now - dt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return "たった今"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}分前"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}時間{minutes % 60}分前"
        return f"{hours // 24}日前"
    except Exception:
        return "不明"


def render_error(msg, cache_data=None):
    """Render error state, falling back to cache if available."""
    if cache_data and "five_hour" in cache_data:
        render_output(cache_data, from_cache=True)
        return

    print("C:-- | size=12 color=#333333")
    print("---")
    if msg == "applescript_js_disabled":
        print("Chrome設定が必要 | color=#ff4444 size=14")
        print("---")
        print("Chrome > 表示 > デベロッパー > | size=12 color=#333333")
        print("「Apple EventsからのJavaScriptを許可」 | size=12 color=#333333")
        print("を有効にしてください | size=12 color=#333333")
    elif msg == "chrome_not_running":
        print("Chromeが起動していません | color=#ff8800 size=14")
        print("---")
        print("Chromeを起動してください | size=12 color=#333333")
    elif msg == "no_chrome_window":
        print("Chromeウィンドウがありません | color=#ff8800 size=14")
    else:
        print(f"エラー: {msg[:60]} | color=#ff4444 size=13")
    print("---")
    print("🔄 今すぐ更新 | refresh=true")
    print("---")
    print("claude.ai/settings/usage を開く | href=https://claude.ai/settings/usage")
    print("---")
    print("⏻ 終了 (watchdogも停止) | bash=/bin/sh param1=-c param2=launchctl\\ unload\\ ~/Library/LaunchAgents/com.swiftbar.watchdog.plist\\ 2>/dev/null\\;\\ killall\\ SwiftBar terminal=false")


def main():
    org_id = get_org_id()
    if not org_id:
        render_error("org_id not found in ~/.claude.json")
        return

    cache_data = load_cache()
    data = fetch_usage_via_chrome(org_id)

    if "error" in data:
        render_error(data["error"], cache_data)
        return

    save_cache(data)
    render_output(data)


if __name__ == "__main__":
    main()
