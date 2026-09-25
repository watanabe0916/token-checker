#!/bin/bash
# トークンが切れたときに復旧する。まず Claude Code 本体に更新させ、
# それで直らなければブラウザでログインする。
#   ./login.command               復旧を試みる（有効なトークンでも再ログインする）
#   ./login.command --if-expired  トークンが切れている（残り 30 分未満を含む）ときだけ
# claude が PATH に無くても、VSCode 拡張に同梱されたものを探して使う。
cd "$(dirname "$0")" || exit 1

# 保存済みトークンの期限（ミリ秒）。読めなければ 0。トークン自体は出力しない。
expires_at() {
    .venv/bin/python -c '
from claude_usage.credentials import load_oauth
try:
    print(int(load_oauth().get("expiresAt") or 0))
except Exception:
    print(0)
' 2>/dev/null || echo 0
}

# 起動直後にまた切れて二度手間にならないよう、残り 30 分未満も期限切れ扱いにする
is_fresh() {
    [ "$1" -gt $(( ($(date +%s) + 1800) * 1000 )) ]
}

if [ "$1" = "--if-expired" ] && is_fresh "$(expires_at)"; then
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

# Claude Code は起動時の初期化で、期限切れのときだけ自分でトークンを更新して保存する
# （refreshOAuthTokenIfNeeded）。推論を伴わない auth status で起動し、それを走らせる。
# 認証情報を書き換えるのは本体だけで、このアプリは結果の期限を読み直すだけ。
# auth status で更新が走ることは実機未検証。走らなければ期限は変わらず、下のログインに進む。
before="$(expires_at)"
"$CLAUDE" auth status >/dev/null 2>&1
after="$(expires_at)"
if [ "$after" -gt "$before" ] && is_fresh "$after"; then
    echo "Claude Code がトークンを更新しました。ログインは不要です。"
    exit 0
fi

echo "ブラウザで Claude にログインしてください…"
exec "$CLAUDE" auth login
