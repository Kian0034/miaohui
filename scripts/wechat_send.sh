#!/bin/zsh
# 用法: wechat_send.sh /绝对/路径/文件.zip
# 流程：复制文件 → 激活微信 → 搜索"文件传输助手" → 粘贴 → 发送
set -e
FILE="$1"
[ -f "$FILE" ] || { echo "文件不存在: $FILE"; exit 1; }

# 1) 文件入剪贴板（Finder 语义，微信可识别为文件）
osascript -e 'on run argv
  set f to POSIX file (item 1 of argv)
  tell application "Finder" to set the clipboard to (f as «class furl»)
end run' "$FILE"

# 2) 激活微信并打开搜索
osascript <<'EOF'
tell application "WeChat" to activate
delay 1.5
tell application "System Events"
  tell process "WeChat"
    set frontmost to true
  end tell
  delay 0.5
  keystroke "f" using command down
  delay 1.2
  keystroke "文件传输助手"
  delay 2.0
  key code 36  -- Return：打开会话
end tell
EOF

# 3) 粘贴文件并发送
osascript <<'EOF'
delay 1.0
tell application "System Events"
  keystroke "v" using command down
  delay 2.5
  key code 36  -- Return：发送
end tell
EOF

echo "已执行发送流程，请人工或截图核验。"
