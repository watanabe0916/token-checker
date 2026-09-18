"""Claude Code の OAuth 認証情報を読み出す。

読み取り専用。トークンをログやファイルに書き出すことは一切しない。
保存場所は Claude Code 本体と同じで、優先順は Keychain → ~/.claude/.credentials.json。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

# Keychain のサービス名。Claude Code は CLAUDE_CONFIG_DIR を使っている場合だけ
# 設定ディレクトリの sha256 先頭 8 桁をサフィックスとして足す。
_SERVICE_BASE = "Claude Code-credentials"


class CredentialError(RuntimeError):
    """認証情報を取得できなかった。メッセージはユーザー向けの日本語。"""


def _config_dir() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".claude"


def _service_name() -> str:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if not env:
        return _SERVICE_BASE
    digest = hashlib.sha256(env.encode("utf-8")).hexdigest()[:8]
    return f"{_SERVICE_BASE}-{digest}"


def _from_keychain() -> dict | None:
    account = os.environ.get("USER") or ""
    attempts = [["-a", account]] if account else []
    attempts.append([])
    for extra in attempts:
        cmd = ["security", "find-generic-password", "-s", _service_name(), *extra, "-w"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout.strip())
            except json.JSONDecodeError:
                continue
    return None


def _from_file() -> dict | None:
    path = _config_dir() / ".credentials.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def load_oauth() -> dict:
    """claudeAiOauth ブロックを返す。

    返す辞書には accessToken / expiresAt などが入る。呼び出し側は
    accessToken を Authorization ヘッダに載せる以外の用途に使わないこと。
    """
    blob = _from_keychain() or _from_file()
    if blob is None:
        raise CredentialError(
            "Claude Code の認証情報が見つかりません。ターミナルで claude にログインしてください。"
        )
    oauth = blob.get("claudeAiOauth")
    if not isinstance(oauth, dict) or not oauth.get("accessToken"):
        raise CredentialError(
            "認証情報の形式が想定と違います。Claude Code を再ログインしてください。"
        )
    return oauth


def is_expired(oauth: dict, skew_seconds: int = 60) -> bool:
    """アクセストークンの有効期限が切れている（または切れかけ）か。

    期限切れでも自前でリフレッシュはしない。Claude Code 本体を使えば
    自動で更新されるので、こちらは次回のポーリングで新しい値を読み直す。
    """
    import time

    expires_at = oauth.get("expiresAt")
    if not isinstance(expires_at, (int, float)):
        return False
    return (expires_at / 1000.0) - skew_seconds <= time.time()
