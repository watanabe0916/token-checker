# claude-usage-menubar

Claude の **5 時間セッション枠の使用率**を macOS のメニューバーに常時表示する常駐アプリ。
ブラウザで「設定 → 使用量」を開かなくても、残り何％・あと何分でリセットかが常に見える。

```
⏱ 🟡 56% · 29m      ← メニューバー
   ↓ クリック
   セッション (5h)　56%
     █████████░░░░░░░
     リセット 00:40（あと 29m）
   ────────────────
   最終更新 00:10:28
   今すぐ更新
   終了
```

## この数字について

5 時間枠は **Web チャットと Claude Code で共有された 1 つのカウンタ**（統合レート制限）。
そのため取得元は 1 箇所でよく、VSCode の Claude Code で使った分も claude.ai で
チャットした分も、どちらもこの％に反映される。

値は Claude Code 本体が `/usage` で使っているのと同じエンドポイント
`GET https://api.anthropic.com/api/oauth/usage` から取っているので、
claude.ai の使用量ページと同じ数字になる。

## セットアップ

```bash
./setup.command     # .venv を作って依存を入れる（初回のみ）
./run.command       # 起動
```

`setup.command` は `/usr/local/bin/python3`（Homebrew の 3.12）を使う。
別の Python を使いたいときは `PYTHON=/path/to/python3 ./setup.command`。

### ログイン時に自動起動する

```bash
./install-login-item.command     # 登録
./uninstall-login-item.command   # 解除
```

`~/Library/LaunchAgents/com.wkout.claude-usage.plist` を作って `launchctl` に登録する。
`KeepAlive` を付けているので、落ちても自動で上がり直す。

## 認証

Claude Code がすでに保存している OAuth トークンを**読むだけ**。
新たにログインを求めたり、トークンを書き換えたりはしない。

読む場所は Claude Code 本体と同じで、優先順に:

1. Keychain のサービス `Claude Code-credentials`
2. `~/.claude/.credentials.json`

初回起動時に Keychain のアクセス許可を 1 回聞かれる。「常に許可」を選べば以降は出ない。

### トークンの有効期限について

アクセストークンが切れた場合、このアプリは**自前でリフレッシュしない**
（Claude Code が持っているリフレッシュトークンを書き換えてしまうリスクを避けるため）。
代わりにメニューバーが `⚠️` 表示になる。Claude Code を一度使えばトークンが更新され、
次のポーリング（最大 60 秒後）で自動的に復帰する。

## 表示の見かた

| 表示 | 意味 |
| --- | --- |
| 🟢 | 50% 未満 |
| 🟡 | 50〜80% |
| 🔴 | 80% 以上 |
| ⚠️ | 取得失敗（直前の値を表示したまま）または未取得 |

更新は 60 秒ごと。メニューの「今すぐ更新」で手動取得もできる。

## 構成

| ファイル | 役割 |
| --- | --- |
| `claude_usage/credentials.py` | Keychain / ファイルから OAuth トークンを読む |
| `claude_usage/usage.py` | 使用量 API を叩いて正規化する。単体でも実行可 |
| `claude_usage/menubar.py` | rumps によるメニューバー常駐 |

API の生レスポンスを見たいとき:

```bash
.venv/bin/python -m claude_usage.usage
```
