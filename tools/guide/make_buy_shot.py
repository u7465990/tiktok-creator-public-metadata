from PIL import Image, ImageDraw, ImageFont
import math, os

src = r"C:\Users\user\.dsh\attachments\v1\objects\4c\4c7649ee72815cf27faae6ea8a3e9d0cf4850666b364e2f49f833ea204f12b15"
out_dir = r"C:\Users\user\root\creator-public-data-written-test-candidate\tools\guide"
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "buy-step1.png")

im = Image.open(src).convert("RGB")
W, H = im.size
sx, sy = W / 1638.0, H / 1049.0
d = ImageDraw.Draw(im)

def box(x1, y1, x2, y2):
    return (x1 * sx, y1 * sy, x2 * sx, y2 * sy)

font_path = r"C:\Windows\Fonts\msyh.ttc"
f_big = ImageFont.truetype(font_path, int(46 * sy))
f_small = ImageFont.truetype(font_path, int(34 * sy))

RED = (220, 30, 30)
WHITE = (255, 255, 255)

# 1) 框住「立即选购」
b = box(180, 656, 315, 703)
d.rounded_rectangle(b, radius=int(10 * sy), outline=RED, width=int(6 * sy))

# 2) 说明文字（放在按钮右侧空白处，避免挡住上面的说明文字）
text = "① 点这里「立即选购」"
tb = d.textbbox((0, 0), text, font=f_big)
tw, th = tb[2] - tb[0], tb[3] - tb[1]
tx, ty = 470 * sx, 640 * sy
d.rounded_rectangle((tx - 18 * sy, ty - 14 * sy, tx + tw + 18 * sy, ty + th + 26 * sy),
                    radius=int(10 * sy), fill=WHITE, outline=RED, width=int(3 * sy))
d.text((tx, ty - 6 * sy), text, font=f_big, fill=RED)

# 3) 箭头：从文字左侧指向按钮右侧
start = (tx - 14 * sy, ty + th / 2 + 6 * sy)
end = (b[2] + 6 * sy, (b[1] + b[3]) / 2)
d.line([start, end], fill=RED, width=int(5 * sy))
ang = math.atan2(end[1] - start[1], end[0] - start[0])
size = 22 * sy
for a in (ang + math.radians(155), ang - math.radians(155)):
    d.line([end, (end[0] + size * math.cos(a), end[1] + size * math.sin(a))], fill=RED, width=int(5 * sy))

# 4) 底部提示
tip = "点了它之后：地域改成「新加坡」→ 镜像选 Ubuntu 22.04 → 最低配 → 买 1 个月"
tb2 = d.textbbox((0, 0), tip, font=f_small)
tw2, th2 = tb2[2] - tb2[0], tb2[3] - tb2[1]
x0, y0 = 40 * sx, 800 * sy
d.rounded_rectangle((x0, y0 - 12 * sy, x0 + tw2 + 36 * sy, y0 + th2 + 22 * sy),
                    radius=int(8 * sy), fill=(255, 248, 220), outline=(200, 160, 0), width=int(2 * sy))
d.text((x0 + 18 * sy, y0 - 4 * sy), tip, font=f_small, fill=(120, 90, 0))

im.save(out, "PNG")
print(out, im.size)
