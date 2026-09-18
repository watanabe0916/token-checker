#!/bin/bash
# 常駐を止める。
# LaunchAgent を登録してある場合、KeepAlive で即座に再起動されてしまうので、
# 先に launchd から降ろしてからプロセスを落とす。
# plist ファイル自体は残すので、次回ログイン時にはまた自動起動する。
# 自動起動そのものをやめるなら uninstall-login-item.command。
LABEL="local.claude-usage"

if launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1; then
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null
    echo "自動起動を一時停止しました（次回ログイン時には再び起動します）。"
fi

if pkill -f "claude_usage[.]menubar" 2>/dev/null; then
    echo "常駐を終了しました。"
else
    echo "起動していません。"
fi
