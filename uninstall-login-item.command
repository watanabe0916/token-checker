#!/bin/bash
# 自動起動の登録を解除する。
LABEL="com.wkout.claude-usage"
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
pkill -f "claude_usage[.]menubar" 2>/dev/null
echo "解除しました。"
