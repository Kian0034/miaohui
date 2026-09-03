"""按分镜生成 edge-tts 配音（云希男声），输出 audio/seg01..07.mp3"""
import asyncio, re, subprocess, sys
from pathlib import Path

import edge_tts

FFMPEG = "/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"

VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"  # 稍快，B站节奏
ROOT = Path(__file__).resolve().parent  # video/
OUT = ROOT / "audio"
OUT.mkdir(exist_ok=True)

text = (ROOT / "script.txt").read_text(encoding="utf-8")

# 提取配音稿段落：=== 之后的编号行
segs = []
for line in text.splitlines():
    m = re.match(r"^\d\d\s+(.+)$", line.strip())
    if m and text.find("=== 配音稿") < text.index(line):
        segs.append(m.group(1).strip())
if len(segs) != 7:
    sys.exit(f"期望7段，实际{len(segs)}段: {segs}")


async def gen(i, s):
    mp3 = OUT / f"seg{i:02d}.mp3"
    await edge_tts.Communicate(s, VOICE, rate=RATE).save(str(mp3))
    dur = subprocess.run(
        [FFMPEG, "-i", str(mp3), "-f", "null", "-"],
        capture_output=True, text=True
    ).stderr
    import re as _re
    m = _re.search(r"Duration: (\d+):(\d+):([\d.]+)", dur)
    d = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    print(f"seg{i:02d} {d:.1f}s  {s[:18]}...")


async def main():
    for i, s in enumerate(segs, 1):
        await gen(i, s)


asyncio.run(main())
