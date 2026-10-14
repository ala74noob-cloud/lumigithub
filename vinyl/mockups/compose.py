"""Compose flat-lay product images from renders of the 3D scene (record.png, cover.png, spread.png)."""
from PIL import Image, ImageFilter
import sys
out = sys.argv[1]

def crop(n):
    im = Image.open(n + '.png').convert('RGBA')
    return im.crop(im.getbbox())

rec, cov, spr = crop('record'), crop('cover'), crop('spread')

def shadow(canvas, im, xy, dx, dy, blur, alpha):
    a = im.getchannel('A').point(lambda v: v * alpha // 255)
    sh = Image.new('RGBA', im.size, (18, 22, 28, 0)); sh.putalpha(a)
    pad = blur * 3
    big = Image.new('RGBA', (im.size[0] + 2 * pad, im.size[1] + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(sh, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(big, (xy[0] - pad + dx, xy[1] - pad + dy))

def place(canvas, im, xy, width):
    im = im.resize((width, round(width * im.size[1] / im.size[0])), Image.LANCZOS)
    # weight: a wide soft shadow plus a tight contact shadow
    shadow(canvas, im, xy, 14, 34, 46, 70)
    shadow(canvas, im, xy, 4, 8, 7, 95)
    canvas.alpha_composite(im, xy)
    return im.size

# Layout 1: cover top-left, record top-right, open gatefold below
c1 = Image.new('RGBA', (2400, 2400), (255, 255, 255, 255))
place(c1, cov, (140, 150), 1040)
place(c1, rec, (1250, 190), 1010)
place(c1, spr, (230, 1290), 1940)
c1.convert('RGB').save(f'{out}/flat-lay-grid.jpg', quality=92)

# Layout 2: record sliding out of the right side of the cover
cw = 1450
ch = round(cw * cov.size[1] / cov.size[0])
rw = round(cw * .9)
rx = 230 + cw - round(rw * .46)
c2 = Image.new('RGBA', (rx + rw + 230, ch + 460), (255, 255, 255, 255))
place(c2, rec, (rx, 230 + (ch - rw) // 2), rw)
place(c2, cov, (230, 230), cw)
c2.convert('RGB').save(f'{out}/flat-lay-sleeve-out.jpg', quality=92)
print(c1.size, c2.size)
