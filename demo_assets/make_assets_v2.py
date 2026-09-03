"""demo 素材 v2：系统壁纸做干扰帧 + PIL 画红衣舞者剪影（电影感）"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

A = Path("/Users/ff/miaohui/demo_assets")
W, H = 1920, 1080

# ---------- 干扰帧：系统壁纸转 png ----------
walls = ["Valley Light", "The Beach", "Catalina Sunset"]
outs = ["landscape", "coffee", "desk"]
for w, o in zip(walls, outs):
    src = f"/System/Library/Desktop Pictures/.thumbnails/{w}.heic"
    dst = A / f"{o}.png"
    subprocess.run(["sips", "-s", "format", "png", src, "--out", str(dst)],
                   capture_output=True, check=True)
    print(o, dst.stat().st_size)

# ---------- 主角帧：红衣舞者剪影 ----------
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img)

# 背景：暗室暖光竖向渐变
top = (24, 16, 14)
mid = (58, 34, 22)
bot = (96, 56, 30)
for y in range(H):
    t = y / H
    if t < 0.55:
        k = t / 0.55
        c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
    else:
        k = (t - 0.55) / 0.45
        c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
    d.line([(0, y), (W, y)], fill=c)

# 后窗光斑（左上柔光）
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([120, 60, 780, 560], fill=(70, 45, 25))
glow = glow.filter(ImageFilter.GaussianBlur(120))
img = Image.blend(img, Image.blend(img, glow, 0.0), 0.0)
img = Image.composite(Image.new("RGB", (W, H), (120, 80, 44)), img,
                      glow.convert("L").point(lambda v: min(v, 110)))

d = ImageDraw.Draw(img)

# 地板反光带
for y in range(int(H * 0.82), H):
    t = (y - H * 0.82) / (H * 0.18)
    c = tuple(int(bot[i] * (1 - t * 0.55)) for i in range(3))
    d.line([(0, y), (W, y)], fill=c)

CX = 1060          # 舞者中心
FY = 950           # 足底

def poly(pts, fill):
    d.polygon(pts, fill=fill)

RED_D = (142, 22, 30)
RED_M = (188, 34, 44)
RED_L = (232, 74, 78)
SKIN = (224, 182, 152)

# 阴影
d.ellipse([CX - 260, FY - 28, CX + 260, FY + 22], fill=(30, 18, 12))

# 裙摆（旋转展开的大弧形，三层）
poly([(CX, FY - 500), (CX - 330, FY - 60), (CX - 180, FY - 14),
      (CX + 200, FY - 20), (CX + 340, FY - 90)], RED_D)
poly([(CX, FY - 500), (CX - 240, FY - 90), (CX + 240, FY - 80)], RED_M)
poly([(CX, FY - 480), (CX - 130, FY - 140), (CX + 150, FY - 130)], RED_L)

# 躯干
poly([(CX - 62, FY - 470), (CX + 62, FY - 470), (CX + 80, FY - 660),
      (CX - 80, FY - 660)], RED_M)

# 手臂（上扬舒展）
d.line([(CX - 60, FY - 640), (CX - 250, FY - 780)], fill=SKIN, width=34)
d.line([(CX + 60, FY - 640), (CX + 260, FY - 740)], fill=SKIN, width=34)
for hx, hy in [(CX - 250, FY - 780), (CX + 260, FY - 740)]:
    d.ellipse([hx - 20, hy - 20, hx + 20, hy + 20], fill=SKIN)

# 头颈
d.line([(CX, FY - 660), (CX, FY - 700)], fill=SKIN, width=30)
d.ellipse([CX - 46, FY - 796, CX + 46, FY - 700], fill=SKIN)
# 发髻
d.ellipse([CX - 30, FY - 836, CX + 34, FY - 780], fill=(40, 26, 22))

# 裙摆飘带（右侧扬起）
poly([(CX + 250, FY - 260), (CX + 520, FY - 420), (CX + 560, FY - 330),
      (CX + 300, FY - 180)], RED_D)

img = img.filter(ImageFilter.GaussianBlur(1.2))

# 时间码水印区提示（无文字，录屏时 drawtext 叠加）
img.save(A / "dance_red.png")
print("dance_red", (A / "dance_red.png").stat().st_size)
