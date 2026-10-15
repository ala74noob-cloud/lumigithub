"""中文字幕渲染（Pillow → 透明 PNG）。预览和导出共用这一套布局，保证位置一致。

绘制顺序：底块 → 辉光 → 投影 → 描边文字 → emoji。
"""
from __future__ import annotations

import glob
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
PRESETS_DIR = ROOT / "presets"

BASE_WIDTH = 720
SAFE_WIDTH_RATIO = 0.86        # 720 宽时约 620px
GAP = 12                       # 中文块与原文 bbox 的间距（720 基准）
EMOJI_NATIVE = 109             # Noto Color Emoji 只有 109px 位图

EMOJI_RE = re.compile(
    "(?:[\U0001F1E6-\U0001F1FF]{2}"
    "|[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF]"
    "(?:\uFE0F)?(?:[\U0001F3FB-\U0001F3FF])?(?:\u200D[\U0001F300-\U0001FAFF\u2600-\u27BF](?:\uFE0F)?)*)"
)

FONT_FILES = {
    "medium": ["NotoSansCJKsc-Medium.otf", "NotoSansSC-Medium.otf", "SourceHanSansSC-Medium.otf"],
    "bold": ["NotoSansCJKsc-Bold.otf", "NotoSansSC-Bold.otf", "SourceHanSansSC-Bold.otf"],
    "black": ["NotoSansCJKsc-Black.otf", "NotoSansSC-Black.otf", "SourceHanSansSC-Heavy.otf"],
    "pixel": ["fusion-pixel-12px-proportional-zh_hans.ttf", "fusion-pixel-12px-monospaced-zh_hans.ttf",
              "fusion-pixel-12px-proportional-zh_hans.otf"],
}
FC_WEIGHT = {"medium": "medium", "bold": "bold", "black": "black", "pixel": "bold"}


# ---------- 资源 ----------

def load_presets() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(PRESETS_DIR.glob("*.json"))}


def save_preset(name: str, preset: dict) -> None:
    name = re.sub(r"[^\w\-]+", "-", name).strip("-") or "custom"
    preset = {**preset, "name": name}
    (PRESETS_DIR / f"{name}.json").write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")


@lru_cache(maxsize=None)
def font_path(kind: str) -> tuple[str, bool]:
    """返回 (路径, 是否像素体)。优先 fonts/ 目录，其次系统中文字体。"""
    for name in FONT_FILES.get(kind, []):
        p = FONTS_DIR / name
        if p.exists():
            return str(p), kind == "pixel"
    if kind == "pixel":
        hits = sorted(glob.glob(str(FONTS_DIR / "fusion-pixel*")))
        if hits:
            return hits[0], True
        kind = "bold"
    for name in FONT_FILES.get(kind, []) + FONT_FILES["bold"]:
        p = FONTS_DIR / name
        if p.exists():
            return str(p), False
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", f":lang=zh-cn:weight={FC_WEIGHT.get(kind, 'bold')}"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if out:
            return out, False
    except (OSError, subprocess.SubprocessError):
        pass
    raise RuntimeError("找不到中文字体，请把 Noto Sans CJK SC 放进 fonts/（见 fonts/README.md）")


@lru_cache(maxsize=None)
def _font(kind: str, size: int) -> tuple[ImageFont.FreeTypeFont, bool]:
    path, pixel = font_path(kind)
    return ImageFont.truetype(path, 12 if pixel else size), pixel


@lru_cache(maxsize=None)
def emoji_font_path() -> str | None:
    for p in [FONTS_DIR / "NotoColorEmoji.ttf", Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
              Path("/System/Library/Fonts/Apple Color Emoji.ttc"), Path("C:/Windows/Fonts/seguiemj.ttf")]:
        if p.exists():
            return str(p)
    return None


@lru_cache(maxsize=512)
def _emoji(ch: str, height: int) -> Image.Image | None:
    path = emoji_font_path()
    if not path:
        return None
    try:
        font = ImageFont.truetype(path, EMOJI_NATIVE)
    except OSError:
        font = ImageFont.truetype(path, 64)
    img = Image.new("RGBA", (EMOJI_NATIVE * 3, EMOJI_NATIVE * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((0, 0), ch, font=font, embedded_color=True)
    bbox = img.getbbox()
    if not bbox:
        return None
    img = img.crop(bbox)
    w = max(1, round(img.width * height / img.height))
    return img.resize((w, height), Image.LANCZOS)


def _rgba(color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), round(255 * opacity)


# ---------- 排版 ----------

def _runs(line: str) -> list[tuple[str, bool]]:
    runs, pos = [], 0
    for m in EMOJI_RE.finditer(line):
        if m.start() > pos:
            runs.append((line[pos:m.start()], False))
        runs.append((m.group(0), True))
        pos = m.end()
    if pos < len(line):
        runs.append((line[pos:], False))
    return runs


class _Measure:
    def __init__(self, kind: str, size: int):
        self.font, self.pixel = _font(kind, size)
        self.size = size
        self.scale = size / 12 if self.pixel else 1.0
        self.emoji_h = round(size * 1.0)

    def text_w(self, s: str) -> float:
        return self.font.getlength(s) * self.scale

    def line_w(self, line: str) -> float:
        w = 0.0
        for s, is_emoji in _runs(line):
            if is_emoji:
                for m in EMOJI_RE.finditer(s):
                    e = _emoji(m.group(0), self.emoji_h)
                    w += (e.width if e else self.emoji_h) + self.size * 0.08
            else:
                w += self.text_w(s)
        return w


def merged_style(cue: dict, presets: dict[str, dict]) -> dict:
    base = presets.get(cue.get("style") or "gold") or presets.get("gold") or next(iter(presets.values()))
    style = json.loads(json.dumps(base))
    for k, v in (cue.get("style_override") or {}).items():
        if isinstance(v, dict) and isinstance(style.get(k), dict):
            style[k].update(v)
        else:
            style[k] = v
    return style


def layout(cue: dict, style: dict, W: int, H: int) -> dict:
    """计算字号、每行宽度和块的位置（不画图）。前端预览的定位也来自这里。"""
    k = W / BASE_WIDTH
    lines = [l for l in cue.get("lines") or [] if l.strip()]
    size = max(8, round(style.get("size", 30) * k))
    safe_w = W * SAFE_WIDTH_RATIO
    warnings = []
    meas = _Measure(style.get("font", "bold"), size)
    widest = max((meas.line_w(l) for l in lines), default=0)
    if widest > safe_w:  # 任何一行都不能超出安全宽度：自动缩小字号并给出警告
        size = max(8, int(size * safe_w / widest))
        meas = _Measure(style.get("font", "bold"), size)
        warnings.append("文字超出安全宽度，已自动缩小字号")
    line_h = round(size * style.get("line_spacing", 1.28))
    widths = [meas.line_w(l) for l in lines]
    block_h = line_h * len(lines)
    gap = round(GAP * k)
    box = style.get("box") or {}
    pad_y = round((box.get("padding") or [0, 0])[1] * k) if box else 0

    bbox = cue.get("source_bbox")
    placement = cue.get("placement", "below")
    custom = cue.get("position")  # 自定义位置：块中心 [x, y]
    cx = (bbox[0] + bbox[2]) / 2 if bbox else W / 2
    if placement == "custom" and custom:
        cx, top = custom[0], custom[1] - block_h / 2
    elif not bbox:
        top = H * 0.72 - block_h
    elif placement == "above":
        top = bbox[1] - gap - pad_y - block_h            # 底边固定，行数变化时向上长
    elif placement == "cover":
        top = (bbox[1] + bbox[3]) / 2 - block_h / 2
    else:  # below：按两行留位，单双行切换时底边不动
        reserve = max(2, len(lines)) * line_h
        top = bbox[3] + gap + pad_y + reserve - block_h
    top = min(max(top, pad_y + 2), H - block_h - pad_y - 2)
    align = style.get("align", "center")
    if placement == "cover" and bbox and align == "left":
        lefts = [bbox[0]] * len(lines)
    else:
        lefts = [min(max(cx - w / 2, 2), W - w - 2) for w in widths]
    return {"size": size, "line_h": line_h, "top": round(top), "lefts": [round(x) for x in lefts],
            "widths": [round(w) for w in widths], "lines": lines, "warnings": warnings, "meas": meas}


# ---------- 绘制 ----------

def _draw_text_layer(L: dict, style: dict, W: int, H: int, fill, stroke_w: int, stroke_fill) -> Image.Image:
    meas: _Measure = L["meas"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, line in enumerate(L["lines"]):
        x = L["lefts"][i]
        y = L["top"] + i * L["line_h"] + (L["line_h"] - L["size"]) // 2
        for s, is_emoji in _runs(line):
            if is_emoji:
                for m in EMOJI_RE.finditer(s):
                    e = _emoji(m.group(0), meas.emoji_h)
                    w = e.width if e else meas.emoji_h
                    x += w + meas.size * 0.08
                continue
            if meas.pixel:
                # 像素体：先按 12px 画，再最近邻放大，保留锯齿；加粗 = 横向偏移 1px 再画一遍
                tw = max(1, int(meas.font.getlength(s)) + 2)
                small = Image.new("RGBA", (tw, 16), (0, 0, 0, 0))
                d = ImageDraw.Draw(small)
                d.text((0, 0), s, font=meas.font, fill=fill)
                d.text((1, 0), s, font=meas.font, fill=fill)
                big = small.resize((round(tw * meas.scale), round(16 * meas.scale)), Image.NEAREST)
                layer.alpha_composite(big, (round(x), round(y)))
            else:
                ImageDraw.Draw(layer).text((x, y), s, font=meas.font, fill=fill,
                                           stroke_width=stroke_w, stroke_fill=stroke_fill)
            x += meas.text_w(s)
    return layer


def _skew(img: Image.Image, amount: float, pivot_y: float) -> Image.Image:
    if not amount:
        return img
    # x' = x + amount * (y - pivot)：基线附近不动，上半部分向右倾
    return img.transform(img.size, Image.AFFINE, (1, amount, -amount * pivot_y, 0, 1, 0), Image.BICUBIC)


def _box_layer(L: dict, style: dict, W: int, H: int) -> Image.Image | None:
    box = style.get("box")
    if not box or not L["lines"]:
        return None
    k = W / BASE_WIDTH
    px, py = (round(v * k) for v in box.get("padding", [12, 6]))
    radius = round(box.get("radius", 0) * k)
    feather = round(box.get("feather", 0) * k)
    color = _rgba(box.get("color", "#000000"), box.get("opacity", 0.6))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rects = []
    if box.get("per_line", True):
        for i, (x, w) in enumerate(zip(L["lefts"], L["widths"])):
            y = L["top"] + i * L["line_h"]
            rects.append((x - px, y - py, x + w + px, y + L["line_h"] + py))
    else:
        x0 = min(L["lefts"])
        x1 = max(x + w for x, w in zip(L["lefts"], L["widths"]))
        rects.append((x0 - px, L["top"] - py, x1 + px, L["top"] + L["line_h"] * len(L["lines"]) + py))
    for r in rects:
        d.rounded_rectangle(r, radius=radius, fill=color)
    if feather:
        # 羽化底条：只模糊 alpha，颜色不变，无硬边
        alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(feather))
        layer = Image.new("RGBA", (W, H), color[:3] + (0,))
        layer.putalpha(alpha)
    return layer


def render(cue: dict, presets: dict[str, dict], W: int, H: int) -> dict:
    """返回 {"image": 裁好的 RGBA PNG（可能为 None）, "x", "y", "warnings"}。"""
    style = merged_style(cue, presets)
    L = layout(cue, style, W, H)
    if not L["lines"]:
        return {"image": None, "x": 0, "y": 0, "warnings": L["warnings"]}
    k = W / BASE_WIDTH
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    box = _box_layer(L, style, W, H)
    if box:
        canvas.alpha_composite(box)

    fill = _rgba(style.get("fill", "#FFFFFF"))
    stroke = style.get("stroke") or {}
    stroke_w = round(stroke.get("width", 0) * k)
    stroke_fill = _rgba(stroke.get("color", "#000000")) if stroke_w else None
    pivot = L["top"] + L["line_h"] * len(L["lines"])
    skew = float(style.get("skew", 0) or 0)

    glow = style.get("glow")
    if glow:
        g = _draw_text_layer(L, style, W, H, _rgba(glow.get("color", "#FFFFFF"), glow.get("opacity", 0.8)), stroke_w, None)
        g = _skew(g, skew, pivot).filter(ImageFilter.GaussianBlur(glow.get("radius", 6) * k))
        canvas.alpha_composite(g)
        canvas.alpha_composite(g)

    shadow = style.get("shadow")
    if shadow:
        sc = _rgba(shadow.get("color", "#000000"), shadow.get("opacity", 0.6))
        s = _draw_text_layer(L, style, W, H, sc, stroke_w, sc if stroke_w else None)
        s = _skew(s, skew, pivot)
        if shadow.get("blur"):
            s = s.filter(ImageFilter.GaussianBlur(shadow["blur"] * k))
        canvas.alpha_composite(s, (round(shadow.get("dx", 0) * k), round(shadow.get("dy", 2) * k)))

    canvas.alpha_composite(_skew(_draw_text_layer(L, style, W, H, fill, stroke_w, stroke_fill), skew, pivot))

    # emoji 单独贴图（彩色位图不能描边/斜切）
    meas: _Measure = L["meas"]
    for i, line in enumerate(L["lines"]):
        x = L["lefts"][i]
        y = L["top"] + i * L["line_h"] + (L["line_h"] - meas.emoji_h) // 2
        for s, is_emoji in _runs(line):
            if not is_emoji:
                x += meas.text_w(s)
                continue
            for m in EMOJI_RE.finditer(s):
                e = _emoji(m.group(0), meas.emoji_h)
                if e:
                    canvas.alpha_composite(e, (round(x), round(y)))
                x += (e.width if e else meas.emoji_h) + meas.size * 0.08

    bbox = canvas.getbbox()
    if not bbox:
        return {"image": None, "x": 0, "y": 0, "warnings": L["warnings"]}
    warnings = list(L["warnings"])
    src = cue.get("source_bbox")
    if src and cue.get("placement") != "cover" and cue.get("cover", "none") == "none":
        tx0 = min(L["lefts"])
        tx1 = max(x + w for x, w in zip(L["lefts"], L["widths"]))
        ty0, ty1 = L["top"], L["top"] + L["line_h"] * len(L["lines"])
        if tx0 < src[2] and src[0] < tx1 and ty0 < src[3] and src[1] < ty1:
            warnings.append("中文和原文重叠")
    return {"image": canvas.crop(bbox), "x": bbox[0], "y": bbox[1], "warnings": warnings}
