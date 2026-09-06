"""正式演示录制：ffmpeg 全屏录制 + 已验证的 IME 键序驱动三场景

场景1  红衣跳舞 → 帧级命中 07:21 → QuickTime 跳转播放（视频最燃点）
场景2  订单     → OCR 命中后台截图 → Preview 打开原图
场景3  预算 评审 → ASR 命中语音 00:06 → QuickTime 跳到那句话
前置：MiaoHui.app 已运行且模型已预热（做过至少一次搜索）
用法: python3 demo_record2.py [out.mp4]
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
    subprocess.run(["osascript", "-e", script], check=False)


def key(code, mods="", delay=0.12):
    m = f" using {{{mods}}}" if mods else ""
    osa(f'tell application "System Events" to key code {code}{m}')
    time.sleep(delay)


def typ(s, delay=0.09):
    osa(f'tell application "System Events" to keystroke "{s}"')
    time.sleep(delay)


def hotkey_panel():
    key(49, "option down", delay=1.6)   # ⌥Space


def main():
    # 1) 清场：先隐藏其他 App 再开录（避免开场穿帮）
    osa('tell application "Finder" to activate')
    time.sleep(0.8)
    key(4, "command down, option down", delay=1.5)  # ⌘⌥H 隐藏其他
    osa('tell application "System Events" to tell process '
        '"UserNotificationCenter" to click button "好" of window 1')
    time.sleep(0.5)

    # 0) 录屏启动：系统原生 screencapture（硬件编码，实时不掉帧）
    if OUT.exists():
        OUT.unlink()
    rec = subprocess.Popen(["screencapture", "-v", "-x", str(OUT)],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    time.sleep(2.0)

    # ---- 场景1：红衣跳舞 → 07:21 跳转 ----
    hotkey_panel()
    typ("hongyi"); key(18, delay=0.5)        # 红衣
    typ("tiaowu"); key(18, delay=0.6)        # 跳舞
    time.sleep(3.0)                          # 等结果
    key(36, delay=2.0)                       # Return → QuickTime 07:21 播放
    key(53, delay=1.0)                       # Esc 收面板（让播放器当主角）
    time.sleep(6.0)                          # 让跳舞画面完整出现
    osa('tell application "QuickTime Player" to pause')
    time.sleep(1.0)
    osa('tell application "QuickTime Player" to quit saving no')
    time.sleep(1.5)

    # ---- 场景2：订单 → OCR 命中截图 → 打开原图 ----
    hotkey_panel()
    typ("dingdan"); key(18, delay=0.6)       # 订单
    time.sleep(2.5)
    key(36, delay=2.0)                       # Return → Preview 打开
    key(53, delay=1.0)
    time.sleep(3.0)
    osa('tell application "Preview" to quit saving no')
    time.sleep(1.5)

    # ---- 场景3：预算 评审 → ASR 命中语音 00:06 → 跳到那句话 ----
    hotkey_panel()
    typ("yusuan"); key(18, delay=0.5)        # 预算
    typ(" "); 
    typ("pingshen"); key(18, delay=0.6)      # 评审
    time.sleep(2.5)
    key(36, delay=2.0)                       # Return → QuickTime 00:06 播放
    key(53, delay=1.0)
    time.sleep(6.0)
    osa('tell application "QuickTime Player" to pause')
    time.sleep(1.5)
    key(53, delay=0.5)                       # Esc 收面板

    # 2) 停止：SIGINT 让 screencapture 正常封尾
    time.sleep(1.0)
    import signal as _signal
    alive = rec.poll() is None
    print("recorder alive:", alive, flush=True)
    if alive:
        rec.send_signal(_signal.SIGINT)
        try:
            rec.wait(timeout=20)
        except subprocess.TimeoutExpired:
            rec.kill()
    print("DONE", OUT, OUT.stat().st_size if OUT.exists() else "MISSING", flush=True)


if __name__ == "__main__":
    main()
