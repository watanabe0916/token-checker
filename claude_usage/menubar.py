"""5 時間セッション枠の使用率をメニューバーに常時表示する。

60 秒ごとに取得し直す。取得はバックグラウンドスレッドで行い、
ネットワークが詰まってもメニューバーの操作は固まらないようにしている。
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

import rumps

from .usage import Limit, RateLimited, Snapshot, UsageError, fetch, format_duration

REFRESH_SECONDS = 60
BAR_WIDTH = 16

# これより古い値は「⚠️ 古い」扱いにする。取得が一時的に失敗しても、
# 数分以内の値ならそのまま信用して表示したほうが実用的。
STALE_AFTER_SECONDS = 300

# 使用率に応じた信号。しきい値は claude.ai の警告表示に合わせてある。
DOT_OK = "🟢"
DOT_WARN = "🟡"
DOT_HIGH = "🔴"
DOT_ERROR = "⚠️"


def _dot(percent: float) -> str:
    if percent >= 80:
        return DOT_HIGH
    if percent >= 50:
        return DOT_WARN
    return DOT_OK


def _bar(percent: float) -> str:
    filled = round(percent / 100 * BAR_WIDTH)
    filled = max(0, min(BAR_WIDTH, filled))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


class UsageApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Claude", title="⏱ …", quit_button="終了")
        self.item_percent = rumps.MenuItem("取得中…")
        self.item_bar = rumps.MenuItem("")
        self.item_reset = rumps.MenuItem("")
        self.item_updated = rumps.MenuItem("")
        self.item_refresh = rumps.MenuItem("今すぐ更新", callback=self.on_refresh)
        self.menu = [
            self.item_percent,
            self.item_bar,
            self.item_reset,
            None,
            self.item_updated,
            self.item_refresh,
        ]
        self._lock = threading.Lock()
        self._snapshot: Snapshot | None = None
        self._error: str | None = None
        self._dirty = True
        self._last_title = ""
        self._backoff_until = 0.0
        self.refresh_async()

    # --- タイマー -----------------------------------------------------------

    @rumps.timer(REFRESH_SECONDS)
    def on_timer(self, _sender) -> None:
        self.refresh_async()

    @rumps.timer(2)
    def on_tick(self, _sender) -> None:
        """描画は必ずこのメインスレッドのタイマー上で行う。

        取得はバックグラウンドスレッドなので、そこから直接 AppKit を触らない。
        新しい結果が来たとき（_dirty）と、表示が変わるときだけ描き直す。
        """
        with self._lock:
            dirty = self._dirty
            self._dirty = False
        if dirty or self._title_changed():
            self.render()

    def on_refresh(self, _sender) -> None:
        self.refresh_async()

    # --- 取得 ---------------------------------------------------------------

    def refresh_async(self) -> None:
        threading.Thread(target=self._refresh, daemon=True).start()

    def _refresh(self) -> None:
        with self._lock:
            if time.time() < self._backoff_until:
                # 間隔制限で待たされている最中。ここで叩くと待ち時間が延びるだけ。
                return

        try:
            snapshot = fetch()
            error = None
        except RateLimited as exc:
            with self._lock:
                self._backoff_until = time.time() + exc.retry_after
            snapshot = None
            error = str(exc)
        except UsageError as exc:
            snapshot = None
            error = str(exc)
        except Exception as exc:  # 取得の失敗で常駐ごと落とさない
            snapshot = None
            error = f"想定外のエラー: {exc}"

        with self._lock:
            if snapshot is not None:
                self._snapshot = snapshot
            self._error = error
            self._dirty = True

    # --- 描画 ---------------------------------------------------------------

    def _title_changed(self) -> bool:
        """残り時間の表示（分単位）が変わったかどうか。"""
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None or snapshot.five_hour is None:
            return False
        limit = snapshot.five_hour
        if limit.percent is None:
            return False
        return self._last_title != self._compose_title(limit, stale=False)

    def _compose_title(self, limit: Limit, stale: bool) -> str:
        dot = DOT_ERROR if stale else _dot(limit.percent)
        return f"{dot} {limit.percent:.0f}% · {format_duration(limit.seconds_left)}"

    def render(self) -> None:
        with self._lock:
            snapshot = self._snapshot
            error = self._error

        limit = snapshot.five_hour if snapshot else None
        if limit is None or limit.percent is None:
            self.title = f"{DOT_ERROR} --%"
            self.item_percent.title = error or "利用状況を取得できません"
            self.item_bar.title = ""
            self.item_reset.title = ""
            self.item_updated.title = ""
            return

        age = time.time() - snapshot.fetched_at
        self._render_limit(limit, stale=age > STALE_AFTER_SECONDS, snapshot=snapshot, error=error)

    def _render_limit(
        self, limit: Limit, stale: bool, snapshot: Snapshot, error: str | None
    ) -> None:
        percent = limit.percent
        left = format_duration(limit.seconds_left)

        self.title = self._compose_title(limit, stale)
        self._last_title = self._compose_title(limit, stale=False)
        self.item_percent.title = f"セッション (5h)　{percent:.0f}%"
        self.item_bar.title = f"  {_bar(percent)}"

        if limit.resets_at is not None:
            reset_at = datetime.fromtimestamp(limit.resets_at).strftime("%H:%M")
            self.item_reset.title = f"  リセット {reset_at}（あと {left}）"
        else:
            self.item_reset.title = "  リセット時刻は不明"

        updated = datetime.fromtimestamp(snapshot.fetched_at).strftime("%H:%M:%S")
        self.item_updated.title = (
            f"最終更新 {updated} — {error}" if error else f"最終更新 {updated}"
        )


def main() -> None:
    # Dock にアイコンを出さず、メニューバーだけに常駐させる。
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )
    except ImportError:
        pass

    UsageApp().run()


if __name__ == "__main__":
    main()
