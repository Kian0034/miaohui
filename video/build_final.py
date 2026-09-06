"""秒回MiaoHui B站爆款视频 · 一键成片
按流量密码公式：前3秒钩子 → 实拍演示三连 → 大厂全灭 → 方案 → 信任 → CTA+三连引导
输出: output/final_v1.mp4 (1080p30) + cover.png
"""
import asyncio
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import qrcode

ROOT = Path(__file__).resolve().parent          # video/
AUD = ROOT / "audio"
OUTD = ROOT / "output"
SEG = OUTD / "segs"
FF = "/Users/ff/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
DEMO = OUTD / "demo_cfr.mp4"                    # 30fps 恒定帧率演示录屏
BGM = ROOT / "bgm" / "goodnightmare.mp3"        # FreePD CC0

W, H = 1920, 1080
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ACCENT = (102, 168, 255)
GREEN = (80, 200, 140)
RED = (255, 92, 92)
WHITE = (245, 247, 255)
GRAY = (140, 148, 160)
BG = (10, 14, 20)

for p in (SEG,):
    p.mkdir(parents=True, exist_ok=True)


def f(size, idx=0):
    return ImageFont.truetype(FONT, size, index=idx)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit(f"FAIL: {cmd[:6]}")
    return r


def dur(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


# ============ 1) 配音文案（与演示画面精确对齐） ============
NARR = [
    "你电脑里躺着几万张截图、几千个视频。你要找的那一张，永远找不到。",
    "看好了。按下快捷键，输入“红衣跳舞”。零点二五秒，直接命中。回车——跳回原视频，七分二十一秒。",
    "截图里的文字也能搜——OCR读过每一张图。搜“订单”，零点三六秒，原图出来。",
    "视频里说过的话，也能搜。所有语音都转成了文字。搜“预算评审”，直接跳到说那句话的第六秒。",
    "这种软件，大厂没做吗？做了。Rewind，被Meta收购，一个月后关停。Screenpipe，开源转收费，一年三百美元。Windows Recall，上线三个月就被安全研究员打穿，截图随便读。",
    "所以我自己写了一个，叫“秒回”。视频帧级索引，加语音转文字，三路检索，本地向量匹配。零点三秒出结果，纯离线，断网照样用。",
    "最关键的，是安全。一个字节都不上传，缩略图全部加密，密钥只在你自己的钥匙串里。银行和密码管理器，默认不索引，每一步都有审计日志。",
    "开源，免费，Mac版现在就能下载，链接在视频简介。找不到东西的痛，从今天起，结束。",
]


def gen_tts():
    import edge_tts

    async def one(i, text):
        mp3 = AUD / f"n{i+1:02d}.mp3"
        await edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+8%").save(str(mp3))

    async def all():
        for i, t in enumerate(NARR):
            await one(i, t)

    asyncio.run(all())
    return [dur(AUD / f"n{i+1:02d}.mp3") for i in range(8)]


# ============ 2) 角标 / CTA二维码 / 结尾三连卡 / 封面 ============
def badge(text, color=ACCENT):
    """整幅1920x1080透明画布，顶部居中圆角角标"""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = f(46)
    tw = d.textlength(text, font=fnt)
    pad, bh = 36, 84
    x0 = (W - tw) / 2 - pad
    y0 = 96
    d.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + bh], 42,
                        fill=(12, 16, 24, 216), outline=color, width=4)
    d.text((W / 2, y0 + bh / 2 - 2), text, font=fnt, fill=WHITE, anchor="mm")
    return img


def make_overlays():
    out = OUTD / "overlays"
    out.mkdir(exist_ok=True)
    badges = {
        "b_hotkey": ("Option+空格 一键唤起", ACCENT),
        "b_025": ("0.25 秒 · 全程离线", GREEN),
        "b_0721": ("07:21 帧级命中", ACCENT),
        "b_ocr": ("OCR 认出截图文字", GREEN),
        "b_orig": ("原图 直接打开", ACCENT),
        "b_asr": ("语音 全部转成文字", GREEN),
        "b_006": ("跳到 00:06", ACCENT),
    }
    for name, (txt, c) in badges.items():
        badge(txt, c).save(out / f"{name}.png")

    # ---- CTA 卡：标题居中在上，二维码居中在下（互不遮挡） ----
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 260), "秒回 MiaoHui", font=f(150), fill=WHITE, anchor="mm")
    d.text((W / 2, 430), "开源 · 免费 · 纯本地 · Mac 版", font=f(66), fill=ACCENT, anchor="mm")
    d.text((W / 2, 565), "下载链接在视频简介", font=f(54), fill=GRAY, anchor="mm")
    qr = qrcode.make("https://pan.quark.cn/s/fef677cdd18b", box_size=10, border=2).convert("RGB")
    qr = qr.resize((330, 330))
    qbg = Image.new("RGB", (370, 410), (245, 247, 255))
    qbg.paste(qr, (20, 20))
    d.rounded_rectangle([775, 620, 1145, 1030], 24, fill=(245, 247, 255))
    img.paste(qbg, (795, 640))
    d.text((960, 1010), "扫码直达下载", font=f(32), fill=(20, 30, 50), anchor="mm")
    img.save(ROOT / "cards" / "cta_qr.png")

    # ---- 结尾三连卡 ----
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 330), "找不到东西的痛", font=f(96), fill=WHITE, anchor="mm")
    d.text((W / 2, 470), "从今天起，结束", font=f(96), fill=ACCENT, anchor="mm")
    labels = [("赞", ACCENT), ("币", (255, 170, 70)), ("藏", GREEN), ("关注", RED)]
    bx = W / 2 - (4 * 200 + 3 * 40) / 2
    for txt, c in labels:
        d.rounded_rectangle([bx, 640, bx + 200, 800], 30, outline=c, width=5)
        d.text((bx + 100, 720), txt, font=f(64), fill=c, anchor="mm")
        bx += 240
    d.text((W / 2, 920), "一键三连 · 下期做手机版", font=f(48), fill=GRAY, anchor="mm")
    img.save(ROOT / "cards" / "endcard.png")

    # ---- 封面（B站投稿封面） ----
    img = Image.new("RGB", (W, H), (6, 9, 14))
    d = ImageDraw.Draw(img)
    d.text((120, 250), "0.3 秒", font=f(260), fill=ACCENT, anchor="lm")
    d.text((125, 520), "找回电脑里丢的那一帧", font=f(110), fill=WHITE, anchor="lm")
    d.text((128, 680), "几万张截图 · 几千个视频 · 一步直达", font=f(56), fill=GRAY, anchor="lm")
    d.rounded_rectangle([125, 780, 760, 880], 24, outline=GREEN, width=6)
    d.text((442, 830), "开源免费 · 纯本地", font=f(56), fill=GREEN, anchor="mm")
    d.text((W - 130, 950), "秒回 MiaoHui", font=f(60), fill=WHITE, anchor="rm")
    img.save(OUTD / "cover.png")
    print("overlays OK")


# ============ 3) 渲染 8 个分镜段 ============
BLURBG = ("split=2[bgm][fgm];"
          "[bgm]scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,boxblur=28:5[bgo];"
          "[fgm]scale=-2:1080[fgo];"
          "[bgo][fgo]overlay=(W-w)/2:0,format=yuv420p")


def zoompan_src(png, seconds, out, zoom=0.08):
    """卡片缓慢推近"""
    d = int(seconds * 30)
    vf = ("scale=2400:1350,"
          f"zoompan=z='1+{zoom}*on/{d}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d=1:s={W}x{H}:fps=30,format=yuv420p")
    run([FF, "-y", "-loop", "1", "-framerate", "30", "-t", str(seconds),
         "-i", str(png), "-vf", vf, "-frames:v", str(d),
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(out)])


def seg_demo(cuts, out, speed=1.0, freeze=0.0, badges=()):
    """演示片段：cuts=[(a,b)] 多段trim→变速→(冻结尾帧)→虚化底→角标
    输入序：前len(cuts)个为录屏段，其后每个角标一个PNG输入"""
    inputs = []
    for a, b in cuts:
        inputs += ["-ss", str(a), "-t", str(b - a), "-i", str(DEMO)]
    ncuts = len(cuts)
    fr = f",tpad=stop_mode=clone:stop_duration={freeze}" if freeze > 0 else ""
    parts = [f"[{i}:v]fps=30{fr},setpts=(PTS-STARTPTS)/{speed}[c{i}]" for i in range(ncuts)]
    vf = (";".join(parts) + ";"
          + "".join(f"[c{i}]" for i in range(ncuts))
          + f"concat=n={ncuts}:v=1[vc];[vc]{BLURBG}[base]")
    last = "base"
    for k, (png, t0, t1) in enumerate(badges):
        vf += (f";[{ncuts + k}:v]format=rgba[o{k}];"
               f"[{last}][o{k}]overlay=0:0:enable='between(t,{t0},{t1})'[v{k + 1}]")
        last = f"v{k + 1}"
    cmd = [FF, "-y"] + inputs
    for png, _, _ in badges:
        cmd += ["-i", str(OUTD / "overlays" / png)]
    cmd += ["-filter_complex", vf, "-map", f"[v{len(badges)}]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(out)]
    run(cmd)


def render_segments():
    # S1 钩子 5.5 + 2.2
    zoompan_src(ROOT / "cards" / "hook.png", 5.5, SEG / "s1a.mp4")
    zoompan_src(ROOT / "cards" / "hook2.png", 2.2, SEG / "s1b.mp4", zoom=0.12)
    run([FF, "-y", "-i", SEG / "s1a.mp4", "-i", SEG / "s1b.mp4",
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         SEG / "s1.mp4"])
    # S2 演示1：红衣跳舞 → 07:21（raw 3.8-14.3）+ 冻结2.0
    seg_demo([(3.8, 14.3)], SEG / "s2.mp4", freeze=2.6,
             badges=[("b_hotkey.png", 0.3, 3.0),
                     ("b_025.png", 4.8, 7.0),
                     ("b_0721.png", 8.6, 12.9)])
    # S3 演示2：订单OCR（切掉崩溃弹窗）1.1x
    seg_demo([(20.7, 26.0), (27.7, 31.2)], SEG / "s3.mp4", speed=1.1,
             badges=[("b_ocr.png", 1.8, 4.6),
                     ("b_orig.png", 5.1, 7.8)])
    # S4 演示3：预算评审 ASR 1.4x
    seg_demo([(36.6, 51.0)], SEG / "s4.mp4", speed=1.4,
             badges=[("b_asr.png", 0.6, 3.1),
                     ("b_006.png", 6.2, 10.2)])
    # S5 大厂全灭 6.6+6.6+6.8
    for card, t in (("rewind", 6.6), ("screenpipe", 6.6), ("recall", 6.8)):
        zoompan_src(ROOT / "cards" / f"{card}.png", t, SEG / f"s5{card}.mp4", zoom=0.10)
    run([FF, "-y", "-i", SEG / "s5rewind.mp4", "-i", SEG / "s5screenpipe.mp4",
         "-i", SEG / "s5recall.mp4",
         "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         SEG / "s5.mp4"])
    # S6 架构 13.5 / S7 信任 14.5
    zoompan_src(ROOT / "cards" / "arch.png", 13.5, SEG / "s6.mp4", zoom=0.06)
    zoompan_src(ROOT / "cards" / "trust.png", 14.5, SEG / "s7.mp4", zoom=0.06)
    # S8 CTA 9.0 + 三连 4.0
    zoompan_src(ROOT / "cards" / "cta_qr.png", 9.0, SEG / "s8a.mp4", zoom=0.05)
    zoompan_src(ROOT / "cards" / "endcard.png", 4.0, SEG / "s8b.mp4", zoom=0.08)
    run([FF, "-y", "-i", SEG / "s8a.mp4", "-i", SEG / "s8b.mp4",
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         SEG / "s8.mp4"])


# ============ 4) 字幕 ASS ============
def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


SUBS = [  # (seg_idx, rel_start, rel_end, text)
    (0, 0.3, 3.6, "你电脑里躺着几万张截图 几千个视频"),
    (0, 3.8, 6.9, "你要找的那一张 永远找不到"),
    (1, 0.3, 2.4, "看好了"),
    (1, 2.6, 5.6, "输入“红衣跳舞”  0.25秒 直接命中"),
    (1, 5.8, 9.6, "回车 → 跳回原视频的 07:21"),
    (2, 0.3, 3.6, "截图里的文字也能搜 — OCR 读了每一张图"),
    (2, 3.8, 6.9, "搜“订单” 0.36秒 原图直接出来"),
    (3, 0.3, 3.2, "说过的话也能搜 — 语音全转成了文字"),
    (3, 3.4, 5.8, "搜“预算 评审”"),
    (3, 6.0, 9.9, "直接跳到那句话的第 6 秒"),
    (4, 0.3, 4.0, "这种软件 大厂没做吗？做了"),
    (4, 4.2, 7.9, "Rewind：被Meta收购 一个月后关停"),
    (4, 8.1, 11.8, "Screenpipe：开源转收费 一年300美元"),
    (4, 12.0, 16.1, "Windows Recall：三个月被安全研究员打穿"),
    (4, 16.3, 19.5, "截图 随便读"),
    (5, 0.3, 3.4, "所以我自己写了一个 叫“秒回”"),
    (5, 3.6, 7.4, "帧级索引 + 语音转文字 · 三路检索"),
    (5, 7.6, 10.4, "本地向量匹配 0.3秒出结果"),
    (5, 10.6, 13.2, "纯离线 · 断网照样用"),
    (6, 0.3, 3.0, "最关键的 是安全"),
    (6, 3.2, 6.4, "一个字节都不上传 · 缩略图全加密"),
    (6, 6.6, 9.6, "密钥只在你自己的钥匙串里"),
    (6, 9.8, 12.3, "银行·密码管理器 默认不索引"),
    (6, 12.5, 14.2, "每一步都有审计日志"),
    (7, 0.3, 4.4, "开源 免费 Mac版现在就能下载"),
    (7, 4.6, 7.2, "链接在视频简介"),
    (7, 7.4, 9.0, "找不到东西的痛 从今天起结束"),
]


def make_ass(starts, total):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narr,Hiragino Sans GB,54,&H00FFFFFF,&H00FFFFFF,&HC8000000,&H96000000,-1,0,0,0,100,100,1,0,1,3,1,2,80,80,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for si, a, b, txt in SUBS:
        t0 = starts[si] + a
        t1 = min(starts[si] + b, total - 0.2)
        lines.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Narr,,0,0,0,,{txt}")
    (OUTD / "subs.ass").write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


# ============ 5) 合成：拼接 + 字幕 + 配音 + BGM（单次重编码） ============
def final_mix(nd):
    segs = [SEG / f"s{i}.mp4" for i in range(1, 9)]
    sd = [dur(p) for p in segs]
    starts = []
    acc = 0.0
    for d in sd:
        starts.append(acc)
        acc += d
    total = sum(sd)
    print("scene starts:", [round(x, 2) for x in starts], "total", round(total, 2))

    make_ass(starts, total)

    fc = ("".join(f"[{i}:v]" for i in range(8))
          + f"concat=n=8:v=1[vcat];[vcat]ass=output/subs.ass[vout];")
    a_in = []
    for i, d in enumerate(nd):
        if d > sd[i] - 0.4:
            print(f"WARN narr{i+1} {d:.1f}s > scene {sd[i]:.1f}s")
        delay = int((starts[i] + 0.35) * 1000)
        a_in.append(f"[{i+8}:a]aresample=44100,aformat=channel_layouts=stereo,"
                    f"adelay={delay}|{delay}[na{i}]")
    bgm_chain = (f"[16:a]aresample=44100,aformat=channel_layouts=stereo,"
                 f"atrim=0:{total:.2f},volume=0.15,"
                 f"afade=t=in:d=0.6,afade=t=out:st={total-4:.2f}:d=4[nbg]")
    mix_in = "".join(f"[na{i}]" for i in range(8)) + "[nbg]"
    fc += ";".join(a_in) + ";" + bgm_chain + ";" + mix_in + (
        f"amix=inputs=9:normalize=0,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]")

    cmd = [FF, "-y"]
    for p in segs:
        cmd += ["-i", str(p)]
    for i in range(8):
        cmd += ["-i", str(AUD / f"n{i+1:02d}.mp3")]
    cmd += ["-i", str(BGM),
            "-filter_complex", fc,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            str(OUTD / "final_v1.mp4")]
    run(cmd)
    print("FINAL:", OUTD / "final_v1.mp4", dur(OUTD / "final_v1.mp4"))


def main():
    print("== TTS ==", flush=True)
    nd = gen_tts()
    print("narr durs:", [round(x, 1) for x in nd], flush=True)
    print("== overlays ==", flush=True)
    make_overlays()
    print("== segments ==", flush=True)
    render_segments()
    print("== mix ==", flush=True)
    final_mix(nd)


if __name__ == "__main__":
    main()
