#!/bin/bash
# メニューバー常駐を起動する。Finder からダブルクリックでも動く。
# 初回（.venv が無いとき）は、先に Python の検出と依存のインストールを行う。
# 作り直したいときは .venv を消してから実行する。
cd "$(dirname "$0")" || exit 1

setup() {
    if [ "$(uname -s)" != "Darwin" ]; then
        echo "このツールは macOS 専用です（メニューバー常駐に rumps / pyobjc を使うため）。" >&2
        return 1
    fi

    # 3.9 以上で、venv を作れる python かどうかを判定する。
    usable() {
        [ -x "$1" ] || return 1
        "$1" -c 'import sys, venv; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null
    }

    # $PYTHON が指定されていればそれを最優先。以降は Homebrew (Apple Silicon →
    # Intel) → PATH 上の python3 → macOS 標準の順。PATH 上の python3 が
    # Anaconda などで古いことがあるので、必ずバージョンを確かめてから使う。
    local py="${PYTHON:-}"
    if [ -n "$py" ]; then
        usable "$py" || { echo "指定された $py は Python 3.9 以上ではありません。" >&2; return 1; }
    else
        for candidate in \
            /opt/homebrew/bin/python3 \
            /usr/local/bin/python3 \
            "$(command -v python3 2>/dev/null)" \
            /usr/bin/python3
        do
            if usable "$candidate"; then py="$candidate"; break; fi
        done
    fi
    if [ -z "$py" ]; then
        echo "Python 3.9 以上が見つかりません。brew install python3 などで入れてください。" >&2
        return 1
    fi

    echo "初回セットアップ: $py ($("$py" -V 2>&1)) で .venv を作ります"
    "$py" -m venv .venv &&
        .venv/bin/pip install --upgrade pip >/dev/null &&
        .venv/bin/pip install -r requirements.txt
}

if [ ! -x .venv/bin/python ]; then
    # 途中で失敗した .venv が残ると次回もセットアップ済みと誤認するので消す
    setup || { rm -rf .venv; exit 1; }
fi

# トークンが切れていれば先にログインする（ブラウザが開く）。有効なら何もしない。
# ログインに失敗しても常駐は起動する。後からメニューの「Claude にログイン…」で再試行できる。
./login.command --if-expired
pkill -f "claude_usage[.]menubar" 2>/dev/null
exec .venv/bin/python -m claude_usage.menubar
