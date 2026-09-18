#!/bin/bash
# ログイン時に自動起動するように LaunchAgent を登録する。
# 解除は uninstall-login-item.command。
set -e
cd "$(dirname "$0")"
REPO="$(pwd)"
LABEL="local.claude-usage"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__REPO__|$REPO|g" "$REPO/$LABEL.plist" > "$DEST"

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$DEST"
echo "登録しました: $DEST"
