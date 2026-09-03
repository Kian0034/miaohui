"""生成宣传视频视觉卡片（深色主题，蓝 #66A8FF，Hiragino 字体）"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (10, 14, 20)
ACCENT = (102, 168, 255)
WHITE = (245, 247, 255)
GRAY = (140, 148, 160)
DARKRED = (255, 92, 92)

F = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def font(size, idx=0):
    return ImageFont.truetype(F, size, index=idx)


def new():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def center(d, y, s, f, fill):
    d.text((W // 2, y), s, font=f, fill=fill, anchor="mm")


def save(img, name):
    img.save(f"cards/{name}.png")
    print(name)


import os

os.makedirs("cards", exist_ok=True)

# ---------- SC01 钩子卡 ----------
img, d = new()
center(d, 380, "你电脑里有", font(110), WHITE)
center(d, 520, "47,000 张截图", font(150), ACCENT)
center(d, 660, "但你永远，找不到想要的那张", font(80), GRAY)
# 底部一条渐变线
for x in range(600, 1320):
    t = (x - 600) / 720
    d.line([(x, 800), (x, 806)], fill=(int(ACCENT[0] * t), int(ACCENT[1] * t), int(ACCENT[2] * t)))
save(img, "hook")

# ---------- SC01b 钩子第二幕：反转 ----------
img, d = new()
center(d, 420, "0.3 秒", font(240), ACCENT)
center(d, 620, "直接命中，跳回那一帧", font(90), WHITE)
save(img, "hook2")

# ---------- SC04 三连痛点卡 ----------
cards = [
    ("rewind", "Rewind AI", "被 Meta 收购", "一个月后 · 直接关停", DARKRED),
    ("screenpipe", "Screenpipe", "开源转付费", "$300/年 · 社区出逃", DARKRED),
    ("recall", "Windows Recall", "上线三个月被安全研究员打穿", "截图随便读 · 无隔离", DARKRED),
]
for name, title, l1, l2, red in cards:
    img, d = new()
    center(d, 300, "大厂做了吗？", font(60), GRAY)
    center(d, 470, title, font(130), WHITE)
    center(d, 640, l1, font(72), red)
    center(d, 750, l2, font(56), GRAY)
    save(img, name)

# ---------- SC05 架构卡 ----------
img, d = new()
center(d, 130, "秒回 MiaoHui · 三路检索引擎", font(72), WHITE)
boxes = [
    (150, "视频帧采样", "关键帧 · 静止去重"),
    (720, "OCR + ASR", "截图文字 · 语音转写"),
    (1290, "CLIP + BGE 向量", "512维 · 语义理解"),
]
for x, t, s in boxes:
    d.rounded_rectangle([x, 280, x + 480, 560], 24, outline=ACCENT, width=4)
    center(d, 380, t, font(52), ACCENT)
    center(d, 470, s, font(38), GRAY)
    d.line([x + 480, 420, x + 540, 420], fill=ACCENT, width=4)
d.polygon([(1770, 400), (1810, 420), (1770, 440)], fill=ACCENT)
d.rounded_rectangle([420, 660, 1500, 900], 24, outline=(80, 200, 140), width=4)
center(d, 740, "RRF 融合 + HNSW 本地索引", font(56), (80, 200, 140))
center(d, 840, "全部在本机 · 断网可用 · 纯离线", font(40), GRAY)
save(img, "arch")

# ---------- SC06 信任卡 ----------
img, d = new()
center(d, 200, "你的隐私，怎么保证？", font(80), WHITE)
rows = [
    ("零上传", "一个字节都不出你的电脑"),
    ("AES-256 加密", "缩略图全加密 · 密钥在系统钥匙串"),
    ("敏感内容默认排除", "银行 · 密码管理器 · 不索引"),
    ("审计日志", "每一笔索引动作可查"),
]
y = 360
for t, s in rows:
    d.ellipse([320, y - 8, 344, y + 16], fill=ACCENT)
    d.text((380, y + 4), t, font=font(56), fill=WHITE, anchor="lm")
    d.text((860, y + 4), s, font=font(44), fill=GRAY, anchor="lm")
    y += 130
save(img, "trust")

# ---------- SC07 CTA 卡（链接占位，二维码后补） ----------
img, d = new()
center(d, 360, "秒回 MiaoHui", font(140), WHITE)
center(d, 500, "开源 · 免费 · Mac 版", font(64), ACCENT)
center(d, 640, "下载链接在视频简介", font(56), GRAY)
save(img, "cta_base")
print("ALL DONE")
