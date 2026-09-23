#!/bin/bash
# Claude にログインする（ブラウザが開く）。
#   ./login.command               常にログインする
#   ./login.command --if-expired  トークンが切れている（残り 30 分未満を含む）ときだけ
# claude が PATH に無くても、VSCode 拡張に同梱されたものを探して使う。
cd "$(dirname "$0")" || exit 1

if [ "$1" = "--if-expired" ] && .venv/bin/python -c '
import sys
from claude_usage.credentials import is_expired, load_oauth
# 起動直後にまた切れて二度手間にならないよう、残り 30 分未満も期限切れ扱いにする
sys.exit(1 if is_expired(load_oauth(), skew_seconds=1800) else 0)
' 2>/dev/null; then
    exit 0
fi

find_claude() {
    if command -v claude >/dev/null 2>&1; then command -v claude; return; fi
    for c in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude"; do
        [ -x "$c" ] && { echo "$c"; return; }
    done
    # 拡張を更新すると古い版のフォルダも残るので、最も新しい版を選ぶ
    ls -d "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null \
        | sort -V | tail -1
}

CLAUDE="$(find_claude)"
if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
    echo "claude コマンドが見つかりません。Claude Code をインストールしてください。" >&2
    exit 1
fi

echo "ブラウザで Claude にログインしてください…"
exec "$CLAUDE" auth login
