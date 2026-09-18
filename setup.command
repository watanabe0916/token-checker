#!/bin/bash
# 初回セットアップ: 使える Python を探して .venv を作り、依存を入れる。
set -e
cd "$(dirname "$0")"

MIN="3.9"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "このツールは macOS 専用です（メニューバー常駐に rumps / pyobjc を使うため）。" >&2
    exit 1
fi

# 3.9 以上で、venv を作れる python かどうかを判定する。
usable() {
    [ -x "$1" ] || return 1
    "$1" -c 'import sys, venv; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null
}

# $PYTHON が指定されていればそれを最優先。以降は Homebrew (Apple Silicon →
# Intel) → PATH 上の python3 → macOS 標準の順。PATH 上の python3 が
# Anaconda などで古いことがあるので、必ずバージョンを確かめてから使う。
PYTHON="${PYTHON:-}"
if [ -n "$PYTHON" ]; then
    usable "$PYTHON" || { echo "指定された $PYTHON は Python $MIN 以上ではありません。" >&2; exit 1; }
else
    for candidate in \
        /opt/homebrew/bin/python3 \
        /usr/local/bin/python3 \
        "$(command -v python3 2>/dev/null)" \
        /usr/bin/python3
    do
        if usable "$candidate"; then PYTHON="$candidate"; break; fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "Python $MIN 以上が見つかりません。brew install python3 などで入れてください。" >&2
    exit 1
fi

echo "使用する Python: $PYTHON ($("$PYTHON" -V 2>&1))"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt

echo
echo "セットアップ完了。./run.command で起動します。"
