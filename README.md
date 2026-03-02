# Claude Fuel Gauge

> Monitor your Claude plan usage limits right from the macOS menu bar.

Stop worrying about hitting rate limits mid-conversation. Claude Fuel Gauge shows your current usage at a glance so you can focus on what matters.

![Claude Fuel Gauge Screenshot](screenshot.png)

## What it shows

| Metric | Description |
|--------|-------------|
| **Session (5h)** | Current session usage, resets every 5 hours |
| **Weekly All Models** | Weekly limit across all models |
| **Weekly Sonnet** | Weekly Sonnet-only limit |

Color-coded indicators tell you when to pace yourself:
- :green_circle: **Green** < 40% - Plenty of fuel
- :yellow_circle: **Yellow** 40-59% - Moderate usage
- :orange_circle: **Orange** 60-79% - Getting heavy
- :red_circle: **Red** 80%+ - Running low

## Prerequisites

- macOS
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (menu bar plugin framework)
- Google Chrome
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (for `~/.claude.json` config)
- Active Claude Pro/Team plan with a logged-in session on [claude.ai](https://claude.ai)

## Installation

### 1. Install SwiftBar

```bash
brew install --cask swiftbar
```

On first launch, SwiftBar will ask you to choose a plugins directory. Select or create:
```
~/Library/Application Support/SwiftBar/Plugins
```

### 2. Install the plugin

```bash
curl -o "$(defaults read com.ameba.SwiftBar PluginDirectory)/claude-usage.5m.py" \
  https://raw.githubusercontent.com/kaz419/Claude-Fuel-Gauge/main/claude-usage.5m.py
chmod +x "$(defaults read com.ameba.SwiftBar PluginDirectory)/claude-usage.5m.py"
```

### 3. Enable Chrome JavaScript automation

In Google Chrome:
1. Menu bar > **View** > **Developer** > **Allow JavaScript from Apple Events**

This allows the plugin to fetch your usage data via Chrome's authenticated session.

### 4. (Optional) Auto-restart after sleep

SwiftBar may disappear from the menu bar after waking from sleep. To auto-recover, create a launchd watchdog:

```bash
cat > ~/Library/LaunchAgents/com.swiftbar.watchdog.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.swiftbar.watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>pgrep -x SwiftBar || open -a SwiftBar</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.swiftbar.watchdog.plist
```

## How it works

1. Reads your organization UUID from `~/.claude.json` (created by Claude Code)
2. Uses AppleScript to execute a `XMLHttpRequest` in any open `claude.ai` Chrome tab
3. Calls the internal API: `GET /api/organizations/{org_id}/usage`
4. If no `claude.ai` tab exists, one is created automatically in the background
5. Results are cached to `~/.claude-usage-cache.json` for offline display
6. Refreshes every 5 minutes (configurable via filename: `claude-usage.{interval}.py`)

## Configuration

### Refresh interval

Rename the file to change the refresh interval:
```bash
# Every 2 minutes
mv claude-usage.5m.py claude-usage.2m.py

# Every 10 minutes
mv claude-usage.5m.py claude-usage.10m.py
```

### Timezone

Automatically uses your system timezone. No configuration needed.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Menu bar shows `C:--` | Chrome is not running or no `claude.ai` session found |
| "Chrome settings required" error | Enable **View > Developer > Allow JavaScript from Apple Events** in Chrome |
| Stale data (shows `*` in menu bar) | Chrome was closed; cached data is shown. Open Chrome to refresh |
| Plugin disappeared after sleep | Install the [watchdog](#4-optional-auto-restart-after-sleep) |

## License

MIT

## Author

Built by [Kaz](https://github.com/kaz419) with Claude Code.
