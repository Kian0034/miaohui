#!/bin/zsh
# 稳妥版 demo 视频合成：逐段编码 → 文件级 concat → 叠时间码+语音
set -e
FF=/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1
cd /Users/ff/miaohui/demo_assets
rm -rf segs concat_list.txt
mkdir -p segs

FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"

# 时间轴（秒）：
#  0-420: landscape/coffee/desk 循环 14 段 x30s
# 420-443: desk 23s
# 443-463: dance_red 20s（语音在此）
# 463-480: landscape 17s
seg() { # seg <img> <dur> <idx>
  $FF -y -loop 1 -i "$1" -t "$2" -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,format=yuv420p" \
    -c:v libx264 -preset veryfast -crf 19 "segs/seg_$3.mp4" 2>/dev/null
  echo "file 'segs/seg_$3.mp4'" >> concat_list.txt
}

seqs=(landscape coffee desk)
idx=0
for i in $(seq 1 14); do
  seg "${seqs[$(( (i-1) % 3 + 1))]}.png" 30 $idx; idx=$((idx+1))
done
seg desk.png 23 $idx; idx=$((idx+1))
seg dance_red.png 20 $idx; idx=$((idx+1))
seg landscape.png 17 $idx; idx=$((idx+1))

# 文件级拼接（重编码一次保证 pts 连续）
$FF -y -f concat -safe 0 -i concat_list.txt -c:v libx264 -preset veryfast -crf 19 -r 30 segs/joined.mp4 2>/dev/null

# 叠加时间码 + 7:23 语音
$FF -y -i segs/joined.mp4 -i meeting_voice.aiff -filter_complex \
"[0:v]drawtext=fontfile='$FONT':text='%{pts\:hms}':fontsize=48:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=12:x=w-tw-40:y=40[v]" \
-map "[v]" -map 1:a -af "adelay=443000|443000,apad" -t 480 \
-c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k demo_video.mp4 2>&1 | tail -1

ls -lh demo_video.mp4
