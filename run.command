#!/bin/bash
# メニューバー常駐を起動する。Finder からダブルクリックでも動く。
cd "$(dirname "$0")" || exit 1
pkill -f "claude_usage[.]menubar" 2>/dev/null
exec .venv/bin/python -m claude_usage.menubar
