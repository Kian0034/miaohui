"""生成模拟电商订单截图（OCR 演示素材）"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1170, 1600  # iPhone 截图尺寸
img = Image.new("RGB", (W, H), (245, 245, 247))
d = ImageDraw.Draw(img)

F = "/System/Library/Fonts/Hiragino Sans GB.ttc"
try:
    f_big = ImageFont.truetype(F, 56)
    f_mid = ImageFont.truetype(F, 40)
    f_sm = ImageFont.truetype(F, 32)
    f_tiny = ImageFont.truetype(F, 26)
except OSError:
    F = "/System/Library/Fonts/PingFang.ttc"
    f_big = ImageFont.truetype(F, 56)
    f_mid = ImageFont.truetype(F, 40)
    f_sm = ImageFont.truetype(F, 32)
    f_tiny = ImageFont.truetype(F, 26)

# 顶部导航栏
d.rectangle([0, 0, W, 160], fill=(255, 255, 255))
d.text((W // 2, 95), "订单详情", font=f_mid, fill=(0, 0, 0), anchor="mm")

# 订单状态卡片
d.rectangle([30, 190, W - 30, 340], fill=(255, 255, 255), outline=(230, 230, 230))
d.text((60, 245), "等待付款", font=f_big, fill=(255, 90, 0))
d.text((60, 310), "请在 2026-09-03 23:59 前完成支付", font=f_tiny, fill=(150, 150, 150))

# 商品卡片
d.rectangle([30, 370, W - 30, 700], fill=(255, 255, 255), outline=(230, 230, 230))
d.rectangle([60, 400, 240, 580], fill=(240, 240, 245))  # 商品图占位
d.text((270, 430), "无线蓝牙耳机 Pro", font=f_mid, fill=(0, 0, 0))
d.text((270, 500), "白色 / 主动降噪版", font=f_sm, fill=(140, 140, 140))
d.text((270, 580), "¥899.00", font=f_mid, fill=(255, 90, 0))
d.text((W - 60, 660), "x1", font=f_sm, fill=(140, 140, 140), anchor="ra")

# 订单信息
d.rectangle([30, 730, W - 30, 1160], fill=(255, 255, 255), outline=(230, 230, 230))
rows = [
    ("订单编号", "2026090210001878234567"),
    ("付款方式", "花呗"),
    ("收货地址", "浙江省杭州市西湖区文三路 138 号"),
    ("收  件  人", "张先生  138****6678"),
    ("下单时间", "2026-09-02  22:41:35"),
    ("发货时间", "预计 48 小时内发货"),
]
y = 780
for k, v in rows:
    d.text((60, y), k, font=f_sm, fill=(140, 140, 140))
    d.text((320, y), v, font=f_sm, fill=(30, 30, 30))
    y += 70

# 价格明细
d.rectangle([30, 1190, W - 30, 1420], fill=(255, 255, 255), outline=(230, 230, 230))
d.text((60, 1230), "商品总价", font=f_sm, fill=(140, 140, 140))
d.text((W - 60, 1230), "¥899.00", font=f_sm, fill=(30, 30, 30), anchor="ra")
d.text((60, 1300), "运费", font=f_sm, fill=(140, 140, 140))
d.text((W - 60, 1300), "¥0.00", font=f_sm, fill=(30, 30, 30), anchor="ra")
d.text((60, 1370), "实付款", font=f_mid, fill=(255, 90, 0))
d.text((W - 60, 1370), "¥899.00", font=f_mid, fill=(255, 90, 0), anchor="ra")

# 底部按钮
d.rounded_rectangle([W // 2 - 60, 1500, W - 60, 1580], 40, fill=(255, 90, 0))
d.text((W // 2 + 420, 1540), "去支付", font=f_mid, fill=(255, 255, 255), anchor="mm")

img.save("order_screenshot.png")
print("OK", img.size)
