"""生成带烧录英文字幕的测试视频（720×1280，30fps，带音轨）。

用法：python tests/make_sample.py out.mp4
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 720, 1280, 30, 6.0
# (起始帧, 结束帧（不含）, 文字)
CUES = [
    (15, 75, "POV: u give 1 person a high-five"),
    (90, 150, "and now this hand\nbelongs to them"),
]
LOGO = "UPROXX"


def _font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                 "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def frame(i: int, cues=CUES, logo=LOGO) -> bytes:
    t = i / FPS
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    r = (60 + 50 * np.sin(2 * np.pi * (x + t * 0.3))) * np.ones_like(y)
    g = 40 + 60 * y * np.ones_like(x)
    b = 90 + 40 * np.cos(2 * np.pi * (y + t * 0.2)) * np.ones_like(x)
    img = Image.fromarray(np.dstack([r, g, b]).clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    if logo:
        d.text((24, 24), logo, font=_font(28), fill=(255, 255, 255))
    for s, e, text in cues:
        if s <= i < e:
            d.multiline_text((W // 2, 400), text, font=_font(40), fill=(255, 255, 255), anchor="ma",
                             align="center", stroke_width=2, stroke_fill=(0, 0, 0), spacing=8)
    return img.tobytes()


def main(out: str, cues=CUES, logo=LOGO):
    n = int(DUR * FPS)
    p = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={DUR}",
        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out,
    ], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i, cues, logo))
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg failed")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sample.mp4")
