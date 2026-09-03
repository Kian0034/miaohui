#!/bin/zsh
# 合成 8 分钟 demo 视频：1920x1080 30fps，7:23 处红衣跳舞+语音，右上角实时时间码
set -e
cd /Users/ff/miaohui/demo_assets
FF=/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1

# 时长布局（秒）：443=7:23 处放 dance_red 20s，443+20=463 起 landscape 收尾到 480
# 前段循环 landscape/coffee/desk 每段约 30s，用 concat 拼到 443s
rm -f concat.txt
: > concat.txt

# 14 段 x30s = 420s (7:00)
seqs=(landscape coffee desk)
for i in $(seq 0 13); do
  img=${seqs[$((i % 3 + 1))]}
  echo "file '$PWD/${img}.png'" >> concat.txt
  echo "duration 30" >> concat.txt
done
# 420-443: desk 23s
echo "file '$PWD/desk.png'" >> concat.txt
echo "duration 23" >> concat.txt
# 443-463: dance_red 20s (主角)
echo "file '$PWD/dance_red.png'" >> concat.txt
echo "duration 20" >> concat.txt
# 463-480: landscape 17s
echo "file '$PWD/landscape.png'" >> concat.txt
echo "duration 17" >> concat.txt
# 最后一帧重复（concat demuxer 要求）
echo "file '$PWD/landscape.png'" >> concat.txt

FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"
$FF -y -f concat -safe 0 -i concat.txt -i meeting_voice.aiff -filter_complex "
[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,
drawtext=fontfile='$FONT':text='%{pts\:hms}':fontsize=48:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=12:x=w-tw-40:y=40[v]
" -map "[v]" -map 1:a -af "adelay=443000|443000,apad" -t 480 \
-c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k \
demo_video.mp4 2>&1 | tail -2

ls -lh demo_video.mp4
