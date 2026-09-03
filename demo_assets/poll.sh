#!/bin/zsh
# 轮询下载 trae 生成图，直到不再是占位图（172K±）
set -e
cd /Users/ff/miaohui/demo_assets

declare -A P=(
  [dance_red]="A young Chinese woman in a bright red dress dancing joyfully in a sunlit modern living room, graceful motion, warm golden light, photorealistic, cinematic"
  [landscape]="Beautiful mountain lake landscape at sunrise, mist over water, photorealistic, cinematic wide shot"
  [coffee]="Cozy coffee shop interior, latte art on wooden table, warm bokeh lights, photorealistic"
  [desk]="Programmer desk setup with colorful code on large monitor, dark room, neon glow, photorealistic"
)

for name in dance_red landscape coffee desk; do
  (
    prompt=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$P[$name]")
    url="https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=${prompt}&image_size=landscape_16_9"
    for i in $(seq 1 60); do
      curl -sL "$url" -o "${name}.png" 2>/dev/null || true
      sz=$(stat -f%z "${name}.png" 2>/dev/null || echo 0)
      if (( sz > 200000 )); then echo "$name OK ($sz bytes, try $i)"; exit 0; fi
      sleep 5
    done
    echo "$name TIMEOUT"; exit 1
  ) &
done
wait
ls -lh *.png
