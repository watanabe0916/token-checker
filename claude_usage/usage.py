"""claude.ai / Claude Code 共通の利用枠を取得する。

5 時間セッション枠は Web チャットと Claude Code で共有された 1 つのカウンタなので、
このエンドポイントの five_hour がそのまま「設定 → 使用量」に出る％にあたる。
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .credentials import CredentialError, is_expired, load_oauth

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
OAUTH_BETA = "oauth-2025-04-20"
TIMEOUT_SECONDS = 10


def _ssl_context() -> ssl.SSLContext:
    """Homebrew の Python はシステムの CA を見ないので certifi があればそれを使う。"""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()

# API のキー -> 画面に出す名前
LIMIT_LABELS = {
    "five_hour": "セッション (5h)",
    "seven_day": "週間 (7d)",
    "seven_day_opus": "Opus 週間",
    "seven_day_sonnet": "Sonnet 週間",
    "overage": "使用クレジット",
}


class UsageError(RuntimeError):
    """取得に失敗した。メッセージはそのまま画面に出せる日本語。"""


class RateLimited(UsageError):
    """このエンドポイント自体のリクエスト回数制限に当たった。

    モデルの利用枠とは別物で、叩きすぎると 429 と Retry-After が返る。
    次に叩いてよい時刻まで待つこと。Claude Code 本体も同じ枠を使うので、
    こちらが浪費すると本体の /usage や上限警告まで巻き添えで失敗しうる。
    """

    def __init__(self, retry_after: float) -> None:
        super().__init__(
            f"取得の間隔制限に当たりました。{int(retry_after)} 秒後に再取得します。"
        )
        self.retry_after = retry_after


@dataclass
class Limit:
    key: str
    label: str
    percent: float | None
    resets_at: float | None  # epoch 秒
    status: str | None

    @property
    def seconds_left(self) -> float | None:
        if self.resets_at is None:
            return None
        return max(0.0, self.resets_at - time.time())


@dataclass
class Snapshot:
    limits: dict[str, Limit]
    fetched_at: float
    raw: dict

    @property
    def five_hour(self) -> Limit | None:
        return self.limits.get("five_hour")


def _parse_resets_at(value) -> float | None:
    """resetsAt は epoch 秒 / ミリ秒 / ISO8601 のいずれでも来うるので全部受ける。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # 2001 年より先の値なら秒、それより大きすぎるならミリ秒とみなす
        return value / 1000.0 if value > 1e11 else float(value)
    if isinstance(value, str):
        from datetime import datetime

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _parse_percent(entry: dict) -> float | None:
    for key in ("utilization", "utilisation", "percent", "percentUsed"):
        value = entry.get(key)
        if isinstance(value, (int, float)):
            # 0.42 形式で来た場合も 42% に正規化する
            return value * 100.0 if value <= 1.0 else float(value)
    return None


# Retry-After が 0 や欠落で返ることがある。そのまま信じると待たずに叩き直して
# しまい、Claude Code 本体と共有しているこのエンドポイントの枠を削る。下限を敷く。
MIN_BACKOFF_SECONDS = 60.0
DEFAULT_BACKOFF_SECONDS = 300.0


def _retry_after_seconds(exc: urllib.error.HTTPError) -> float:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    try:
        return max(MIN_BACKOFF_SECONDS, float(raw))
    except (TypeError, ValueError):
        return DEFAULT_BACKOFF_SECONDS


def parse(payload: dict) -> Snapshot:
    limits: dict[str, Limit] = {}
    for key, label in LIMIT_LABELS.items():
        entry = payload.get(key)
        if not isinstance(entry, dict):
            continue
        limits[key] = Limit(
            key=key,
            label=label,
            percent=_parse_percent(entry),
            resets_at=_parse_resets_at(entry.get("resetsAt") or entry.get("resets_at")),
            status=entry.get("status"),
        )
    return Snapshot(limits=limits, fetched_at=time.time(), raw=payload)


def fetch() -> Snapshot:
    try:
        oauth = load_oauth()
    except CredentialError as exc:
        raise UsageError(str(exc)) from exc

    if is_expired(oauth):
        raise UsageError("トークンの期限切れです。Claude Code を一度使うと自動更新されます。")

    request = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {oauth['accessToken']}",
            "Content-Type": "application/json",
            "anthropic-beta": OAUTH_BETA,
            "User-Agent": "claude-usage-menubar/1.0",
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=_ssl_context()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise RateLimited(_retry_after_seconds(exc)) from exc
        if exc.code == 401:
            raise UsageError("認証エラー (401)。Claude Code を一度使うか再ログインしてください。") from exc
        raise UsageError(f"取得に失敗しました (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise UsageError(f"ネットワークエラー: {exc.reason}") from exc

    if not isinstance(payload, dict):
        raise UsageError("想定外のレスポンス形式です。")
    return parse(payload)


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    minutes = int(seconds // 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m"


if __name__ == "__main__":
    import sys

    try:
        snapshot = fetch()
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(snapshot.raw, indent=2, ensure_ascii=False))
    print("--- parsed ---")
    for limit in snapshot.limits.values():
        print(
            f"{limit.label}: {limit.percent}% "
            f"reset in {format_duration(limit.seconds_left)} status={limit.status}"
        )
