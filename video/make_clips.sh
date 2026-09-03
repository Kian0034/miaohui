#!/bin/zsh
# 静态卡 → Ken Burns 动画片段（30fps 1080p），时长对齐配音
set -e
FF=/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1
cd /Users/ff/miaohui/video

clip() {  # clip <card> <seconds>
  local name=$1 dur=$2
  local frames=$((dur * 30))
  $FF -y -loop 1 -i "cards/${name}.png" -vf \
    "scale=2112:-2,zoompan=z='min(zoom+0.0006,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=${frames}:s=1920x1080:fps=30,format=yuv420p" \
    -t $dur -c:v libx264 -preset medium -crf 19 "clips/c_${name}.mp4" 2>/dev/null
  echo "c_${name}.mp4 ${dur}s"
}

clip hook     4.0
clip hook2    2.5
clip rewind   6.4
clip screenpipe 6.4
clip recall   6.4
clip arch     13.2
clip trust    14.7
ls -lh clips/c_*.mp4 | awk '{print $5, $9}'
