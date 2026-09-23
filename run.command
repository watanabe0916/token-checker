#!/bin/bash
# メニューバー常駐を起動する。Finder からダブルクリックでも動く。
cd "$(dirname "$0")" || exit 1
# トークンが切れていれば先にログインする（ブラウザが開く）。有効なら何もしない。
# ログインに失敗しても常駐は起動する。後からメニューの「Claude にログイン…」で再試行できる。
./login.command --if-expired
pkill -f "claude_usage[.]menubar" 2>/dev/null
exec .venv/bin/python -m claude_usage.menubar
