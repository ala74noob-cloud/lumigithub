from PIL import Image, ImageFilter, ImageDraw, ImageChops
import sys
out = sys.argv[1]

def crop(n):
    im = Image.open(n + '.png').convert('RGBA')
    return im.crop(im.getbbox())

rec, cov, spr = crop('record'), crop('cover'), crop('spread')
# front view only: trim the rounded spine edge that shows at the left of the jacket
cov = cov.crop((24, 0, cov.size[0], cov.size[1]))

def shrink_wrap(im):
    """Clear shrink-wrap sheen over the cover: a soft diagonal glare and a bright top edge."""
    w, h = im.size
    glare = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(glare)
    d.polygon([(int(w * .55), 0), (int(w * .78), 0), (int(w * .30), h), (int(w * .07), h)], fill=38)
    d.polygon([(int(w * .83), 0), (int(w * .87), 0), (int(w * .39), h), (int(w * .35), h)], fill=26)
    glare = glare.filter(ImageFilter.GaussianBlur(w * .03))
    d2 = ImageDraw.Draw(glare)
    d2.rectangle([0, 0, w, max(2, h // 300)], fill=60)
    white = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    white.putalpha(ImageChops.multiply(glare, im.getchannel('A')))
    o = im.copy(); o.alpha_composite(white); return o

def place(canvas, im, xy, size, shadow=(0, 18, 28, 70)):
    im = im.resize(size, Image.LANCZOS)
    dx, dy, blur, alpha = shadow
    a = im.getchannel('A').point(lambda v: v * alpha // 255)
    sh = Image.new('RGBA', im.size, (20, 24, 30, 0)); sh.putalpha(a)
    pad = blur * 3
    big = Image.new('RGBA', (im.size[0] + 2 * pad, im.size[1] + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(sh, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(big, (xy[0] - pad + dx, xy[1] - pad + dy))
    canvas.alpha_composite(im, xy)

cov_w = shrink_wrap(cov)

# Layout 1: cover top-left, record top-right, open gatefold below
W = 2400
c1 = Image.new('RGBA', (W, W), (255, 255, 255, 255))
place(c1, cov_w, (150, 170), (1020, 1020))
place(c1, rec, (1240, 180), (1000, 1000), shadow=(0, 14, 22, 60))
place(c1, spr, (150, 1330), (2100, int(2100 * spr.size[1] / spr.size[0])))
c1.convert('RGB').save(f'{out}/flat-lay-grid.jpg', quality=92)

# Layout 2: record sliding out of the right side of the cover
cs = 1400
c2 = Image.new('RGBA', (250 + cs - int(cs * .97 * .44) + int(cs * .97) + 250, 1900), (255, 255, 255, 255))
place(c2, rec, (250 + cs - int(cs * .97 * .44), 250 + int(cs * .015)), (int(cs * .97), int(cs * .97)), shadow=(0, 14, 22, 55))
place(c2, cov_w, (250, 250), (cs, cs))
c2.convert('RGB').save(f'{out}/flat-lay-sleeve-out.jpg', quality=92)
print(c1.size, c2.size)
