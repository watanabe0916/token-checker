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
./stop.command      # 停止
```

`setup.command` は使える Python 3.9 以上を自動で探す。探す順は
Homebrew (Apple Silicon → Intel) → PATH 上の `python3` → macOS 標準の `/usr/bin/python3`。
PATH 上の `python3` が Anaconda などで古いことがあるため、必ずバージョンを確認してから使う。
明示したいときは `PYTHON=/path/to/python3 ./setup.command`。

### 動かすのに必要なもの

| | |
| --- | --- |
| macOS | メニューバー常駐に rumps / pyobjc を使うため、macOS 専用 |
| Claude Code | **ログイン済みであること。** このツールは自前でログインせず、Claude Code が保存した認証情報を読むだけ |
| Claude のサブスクリプション | Pro / Max など。5 時間枠という概念があるプランが対象 |
| Python 3.9 以上 | `setup.command` が自動で探す。無ければ `brew install python3` |

`claude` にログインしていない状態では「認証情報が見つかりません」と表示される。
先にターミナルで `claude` を起動してログインすること。

API キー（`ANTHROPIC_API_KEY`）だけで使っている場合は対象外。
このエンドポイントは OAuth 認証専用で、API キー利用は従量課金なので 5 時間枠自体が存在しない。

### フォークした場合

環境依存の値はコードに埋めていないので、fork してそのまま動く。

- LaunchAgent のラベルは `local.claude-usage` という汎用名。同名のものが
  すでにある場合だけ、`*.plist` と install/stop/uninstall の `LABEL` を揃えて変える
- plist 内のパスは `__REPO__` プレースホルダで、`install-login-item.command` が
  実行時に自分の絶対パスへ置換する。リポジトリをどこに置いても動く
- `.venv/` と `menubar.log` は `.gitignore` 済み

## 止め方

| 方法 | 効果 |
| --- | --- |
| メニューバー → 「終了」 | その場で終了 |
| `./stop.command` | その場で終了。自動起動を登録済みなら先に launchd から降ろす |
| `./uninstall-login-item.command` | 終了したうえで、自動起動の登録ごと削除 |

`pkill` による終了は launchd から見ると異常終了なので、自動起動を登録してあると
即座に再起動される。`stop.command` は先に `launchctl bootout` するのでそこを回避できる。
ただし plist は残すので、**次回ログイン時にはまた起動する**。恒久的にやめるなら
`uninstall-login-item.command` を使う。

### ログイン時に自動起動する

```bash
./install-login-item.command     # 登録
./uninstall-login-item.command   # 解除
```

`~/Library/LaunchAgents/local.claude-usage.plist` を作って `launchctl` に登録する。
**登録するまでは自動起動しない。** 登録後に起動するのは次の2つの場合だけ:

| きっかけ | plist のキー |
| --- | --- |
| ログイン（macOS 起動後の初回サインイン、再ログイン、再起動） | `RunAtLoad` |
| 異常終了（クラッシュ、`pkill` などで殺されたとき） | `KeepAlive` = `SuccessfulExit: false` |

メニューの「終了」による正常終了では**起動し直さない**。
`KeepAlive` を無条件 `true` にすると終了した瞬間に launchd が起動し直してしまい、
終了できなくなるため、異常終了時に限定している。

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

更新は 3 分ごと。メニューの「今すぐ更新」で手動取得もできる。

### 更新間隔を 3 分にしている理由

使用量エンドポイントには、モデルの利用枠とは**別に**リクエスト回数の制限がある。
しかもこの枠は Claude Code 本体と共有なので、このツールが叩きすぎると
本体の `/usage` や上限警告まで巻き添えで 429 になる。

5 時間枠の表示にリアルタイム性はほとんど要らない（3 分間隔でも粒度は 1% 未満）ので、
実用上の損失なしに余裕を持たせている。429 を踏んだ場合は
60 秒 → 120 → 240 → 480 → 900 秒（上限）と待ち時間を倍にしていく。
サーバが返す `Retry-After` は `0` のことがあり当てにならないため、
こちら側でも下限と上限を持っている。

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
