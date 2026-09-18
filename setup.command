#!/bin/bash
# 初回セットアップ: 仮想環境を作って依存を入れる。
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-/usr/local/bin/python3}"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt
echo
echo "セットアップ完了。./run.command で起動します。"
