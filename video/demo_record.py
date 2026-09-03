"""录屏自动化：ffmpeg 全屏录制 + osascript 驱动 MiaoHui 三场景演示

场景：
  1. ⌥Space → 粘贴"红衣 跳舞" → 等1.5s → Return → QuickTime 跳到 7:23
  2. ⌥Space → 粘贴"订单编号" → 等1.5s（OCR 命中截图）
  3. ⌥Space → 粘贴"预算评审会" → 等1.5s（ASR 命中视频帧）
用法: python3 demo_record.py [out.mp4]  (默认 output/demo_full.mp4)
"""
import subprocess
import sys
import time
from pathlib import Path

FF = "/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
ROOT = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "demo_full.mp4"
OUT.parent.mkdir(exist_ok=True)


def osa(script):
    subprocess.run(["osascript", "-e", script], check=True)


def key(code, mods=""):
    m = f" using {{{mods}}}" if mods else ""
    osa(f'tell application "System Events" to key code {code}{m}')


def paste(text):
    subprocess.run(["pbcopy"], input=text.encode(), check=True)
    time.sleep(0.3)
    key(9, "command down")  # ⌘V


def snap(name):
    p = ROOT / "clips" / f"{name}.png"
    subprocess.run(["screencapture", "-x", str(p)], check=True)
    return p


def main():
    # 1) 启动录屏（屏幕0，无音频，30fps）
    rec = subprocess.Popen(
        [FF, "-f", "avfoundation", "-i", "1:none", "-pix_fmt", "uyvy422",
         "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-y", str(OUT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)

    # 2) 场景1：红衣跳舞 → 跳转 7:23
    key(49, "option down")          # ⌥Space 唤起面板
    time.sleep(1.2)
    paste("红衣 跳舞")
    time.sleep(2.0)                 # 等检索+缩略图渲染
    snap("s1_results")
    key(36)                         # Return 跳转
    time.sleep(4.5)                 # QuickTime 打开并 seek
    snap("s1_player")

    # 3) 场景2：订单编号 OCR
    key(49, "option down")
    time.sleep(1.0)
    key(0, "command down")          # ⌘A 全选旧词
    key(124, "fn down")             # 确保光标末尾（部分场景需要）
    paste("订单编号")
    time.sleep(2.0)
    snap("s2_ocr")

    # 4) 场景3：预算评审会 ASR
    key(49, "option down")
    time.sleep(1.0)
    key(0, "command down")
    paste("预算评审会")
    time.sleep(2.0)
    snap("s3_asr")
    key(53)                         # Esc 收起面板

    # 5) 停止录屏
    time.sleep(0.8)
    rec.terminate()
    rec.wait(timeout=15)
    print("DONE", OUT, OUT.stat().st_size if OUT.exists() else "MISSING")


if __name__ == "__main__":
    main()
