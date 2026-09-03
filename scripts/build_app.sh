#!/bin/zsh
# 秒回 MiaoHui — macOS .app 构建脚本（可复现构建）
# 依赖：python3 -m pip install pyinstaller
set -e
cd "$(dirname "$0")/.."

python3 -m PyInstaller --noconfirm --clean \
  --windowed \
  --name MiaoHui \
  --osx-bundle-identifier com.miaohui.local-search \
  --hidden-import appdirs \
  --exclude-module pkg_resources \
  --collect-all AppKit \
  --collect-all Foundation \
  --collect-all objc \
  --hidden-import core.pipeline \
  --hidden-import core.bootstrap \
  --hidden-import core.search \
  --hidden-import app.panel \
  --hidden-import app.menubar \
  --hidden-import app.hotkey \
  --hidden-import app.opener \
  main.py

# 剔除被误收集的 lz4（用户站点包元数据损坏 + 无运行时引用；
# 不剔除会让 pkg_resources 运行时钩子以 InvalidVersion 崩溃）
FW="dist/MiaoHui.app/Contents/Frameworks"
RS="dist/MiaoHui.app/Contents/Resources"
rm -rf "$FW/lz4" "$FW"/lz4-*.dist-info "$RS"/lz4-*.dist-info

echo "== dist/MiaoHui.app 构建完成 =="
