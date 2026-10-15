"""烧录字幕检测（指南第 3 部分 A 路径）。

1. 每秒抽 2 帧跑 OCR，找出文字常出现的垂直带，排除整条视频不变的 Logo/水印。
2. 对每个带逐帧算“文字颜色像素”掩码，掩码变化超过阈值就切一段。
3. 每段取中间帧 OCR；相邻且文字相同的段合并（淡入过渡、背景晃动造成的误切）。
4. 在段内多数帧都是文字的像素上求 bbox。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

from . import ocr
from .video import FrameReader

Progress = Callable[[float, str], None]

SAMPLE_FPS = 2.0
MASK_W = 240           # 掩码缩到这个宽度再比较，够用且省内存
CUT_THRESHOLD = 0.35   # 相邻帧掩码差异比例超过它就切段
MIN_ON_FRACTION = 0.004
MIN_SEG_FRAMES = 3
PRESENCE = 0.6         # 段内 ≥60% 帧都是文字的像素才算字形
COLOR_TOL = 70.0


@dataclass
class Band:
    y0: int
    y1: int
    colors: list = field(default_factory=list)   # 候选文字颜色（BGR）
    boxes: list = field(default_factory=list)    # 该带内的 OCR 框


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", text.lower())


def _iou(a, b) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _text_color(frame: np.ndarray, box) -> np.ndarray | None:
    """OCR 框内两类像素中，与外围环形颜色差得更远的那一类视为文字颜色。"""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = box
    pad = 4
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    inner = frame[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    outer = frame[Y0:Y1, X0:X1].astype(np.float32)
    ring = np.concatenate([outer[:pad].reshape(-1, 3), outer[-pad:].reshape(-1, 3),
                           outer[:, :pad].reshape(-1, 3), outer[:, -pad:].reshape(-1, 3)])
    ring_med = np.median(ring, axis=0)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(inner, 2, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    d = np.linalg.norm(centers - ring_med, axis=1)
    return centers[int(np.argmax(d))]


def _dedupe_colors(colors: list[np.ndarray]) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for c in sorted(colors, key=lambda c: -float(c.sum())):
        if all(np.linalg.norm(c - o) > COLOR_TOL for o in out):
            out.append(c)
    return out[:3]


def find_bands(samples: list[tuple[float, np.ndarray, list[dict]]], height: int):
    """返回 (bands, logos)。samples = [(t, frame, ocr_results)]。"""
    n = len(samples)
    # 1) Logo：位置和文字都不变、出现在 ≥80% 抽样帧里
    groups: list[dict] = []
    for _, _, res in samples:
        for r in res:
            key = _norm(r["text"])
            for g in groups:
                if g["key"] == key and _iou(g["box"], r["box"]) > 0.6:
                    g["hits"] += 1
                    break
            else:
                groups.append({"key": key, "box": r["box"], "text": r["text"], "hits": 1})
    logos = [g for g in groups if n >= 4 and g["hits"] >= 0.8 * n]

    def is_logo(r):
        return any(_norm(r["text"]) == g["key"] and _iou(g["box"], r["box"]) > 0.6 for g in logos)

    # 2) 垂直覆盖直方图 → 带
    cover = np.zeros(height, dtype=np.int32)
    kept = []
    for _, frame, res in samples:
        for r in res:
            if is_logo(r):
                continue
            kept.append((frame, r))
            cover[r["box"][1]:r["box"][3]] += 1
    bands: list[Band] = []
    on = cover > 0
    gap = max(6, int(height * 0.015))
    y = 0
    while y < height:
        if not on[y]:
            y += 1
            continue
        y0 = y
        while y < height and (on[y] or on[y:y + gap].any()):
            y += 1
        pad = max(6, int(height * 0.01))
        bands.append(Band(max(0, y0 - pad), min(height, y + pad)))
    for frame, r in kept:
        cy = (r["box"][1] + r["box"][3]) / 2
        for b in bands:
            if b.y0 <= cy < b.y1:
                b.boxes.append(r)
                c = _text_color(frame, r["box"])
                if c is not None:
                    b.colors.append(c)
                break
    for b in bands:
        b.colors = _dedupe_colors(b.colors) or [np.array([255, 255, 255], np.float32)]
    return bands, logos


def _mask(crop: np.ndarray, colors: list[np.ndarray]) -> np.ndarray:
    h, w = crop.shape[:2]
    small = cv2.resize(crop, (MASK_W, max(1, int(h * MASK_W / w))), interpolation=cv2.INTER_AREA).astype(np.float32)
    m = np.zeros(small.shape[:2], bool)
    for c in colors:
        m |= np.linalg.norm(small - c, axis=2) < COLOR_TOL
    return m


def _segments(masks: list[np.ndarray]) -> list[list[int]]:
    """按掩码变化切段，只返回“有字”的段（帧号列表 [start, end] 闭区间）。"""
    segs: list[list[int]] = []
    prev = None
    for i, m in enumerate(masks):
        on = m.mean() > MIN_ON_FRACTION
        if not on:
            prev = None
            continue
        if prev is not None:
            diff = np.logical_xor(m, prev).sum() / max(m.sum(), prev.sum(), 1)
            if diff <= CUT_THRESHOLD:
                segs[-1][1] = i
                prev = m
                continue
        segs.append([i, i])
        prev = m
    # 小于 3 帧的段并到紧邻的段
    merged: list[list[int]] = []
    for s in segs:
        short = s[1] - s[0] + 1 < MIN_SEG_FRAMES
        if merged and merged[-1][1] + 1 == s[0] and (short or merged[-1][1] - merged[-1][0] + 1 < MIN_SEG_FRAMES):
            merged[-1][1] = s[1]
        else:
            merged.append(list(s))
    return merged


def detect(video_path: str, width: int, height: int, fps: float, progress: Progress | None = None) -> dict:
    progress = progress or (lambda f, m: None)
    with FrameReader(video_path) as reader:
        fps = reader.fps or fps
        step = max(1, int(round(fps / SAMPLE_FPS)))
        total = max(1, reader.count)

        # 1. 抽样 OCR
        samples = []
        n_samples = total // step + 1
        for i, frame in reader:
            if i % step == 0:
                samples.append((i / fps, frame, ocr.read(frame)))
                progress(0.4 * len(samples) / n_samples, f"抽样识别 {len(samples)}/{n_samples}")
        bands, logos = find_bands(samples, height)
        del samples
        if not bands:
            return {"cues": [], "logos": [g["text"] for g in logos], "bands": []}

        # 2. 逐帧掩码
        masks: list[list[np.ndarray]] = [[] for _ in bands]
        for i, frame in reader:
            for bi, b in enumerate(bands):
                masks[bi].append(_mask(frame[b.y0:b.y1], b.colors))
            if i % 30 == 0:
                progress(0.4 + 0.3 * i / total, f"切分时间轴 {i}/{total}")

        # 3. 每段 OCR + 合并
        cues = []
        all_segs = [(bi, s) for bi, ms in enumerate(masks) for s in _segments(ms)]
        texted: list[tuple[int, list[int], str, list[dict]]] = []
        for k, (bi, (s0, s1)) in enumerate(all_segs):
            b = bands[bi]
            frame = reader.read_at((s0 + s1) // 2)
            # 整帧 OCR 再按带过滤：裁成窄条后检测模型的缩放会变差，切词出错
            res = [r for r in (ocr.read(frame) if frame is not None else [])
                   if b.y0 <= (r["box"][1] + r["box"][3]) / 2 < b.y1]
            texted.append((bi, [s0, s1], ocr.join_lines(res), res))
            progress(0.7 + 0.25 * (k + 1) / max(1, len(all_segs)), f"读取文字 {k + 1}/{len(all_segs)}")

    texted.sort(key=lambda t: (t[0], t[1][0]))
    groups: list[dict] = []
    for bi, (s0, s1), text, res in texted:
        last = groups[-1] if groups and groups[-1]["band"] == bi else None
        adjacent = last is not None and s0 - last["s1"] <= 2
        if adjacent and (_norm(text) == _norm(last["text"]) or not text or not last["text"]):
            last["s1"] = s1
            last["res"] += res
            if not last["text"]:
                last["text"] = text
            continue
        groups.append({"band": bi, "s0": s0, "s1": s1, "text": text, "res": list(res)})

    for g in groups:
        if not g["text"]:
            continue
        b = bands[g["band"]]
        cues.append({
            "start": round(g["s0"] / fps, 3),
            "end": round((g["s1"] + 1) / fps, 3),
            "source_text": g["text"],
            "source_bbox": _bbox(masks[g["band"]][g["s0"]:g["s1"] + 1], g["res"], b, width),
            "kind": "caption",
        })
    progress(1.0, f"识别完成，共 {len(cues)} 条")
    return {
        "cues": cues,
        "logos": sorted({g["text"] for g in logos}),
        "bands": [[b.y0, b.y1] for b in bands],
    }


def _bbox(seg_masks: list[np.ndarray], res: list[dict], band: Band, width: int) -> list[int]:
    ocr_box = None
    if res:
        xs0, ys0, xs1, ys1 = zip(*[r["box"] for r in res])
        ocr_box = [min(xs0), min(ys0), max(xs1), max(ys1)]
    freq = np.mean(np.stack(seg_masks), axis=0) >= PRESENCE
    scale = width / MASK_W
    if ocr_box is not None:
        pad = 12
        gx0 = max(0, int((ocr_box[0] - pad) / scale))
        gx1 = int((ocr_box[2] + pad) / scale) + 1
        gy0 = max(0, int((ocr_box[1] - band.y0 - pad) / scale))
        gy1 = int((ocr_box[3] - band.y0 + pad) / scale) + 1
        gate = np.zeros_like(freq)
        gate[gy0:gy1, gx0:gx1] = True
        freq &= gate
    ys, xs = np.nonzero(freq)
    if len(xs) == 0:
        return ocr_box or [0, band.y0, width, band.y1]
    box = [int(xs.min() * scale), int(ys.min() * scale) + band.y0,
           int((xs.max() + 1) * scale), int((ys.max() + 1) * scale) + band.y0]
    if ocr_box is not None:  # 掩码可能漏掉 emoji 等非文字颜色部分，用 OCR 框补全
        box = [min(box[0], ocr_box[0]), min(box[1], ocr_box[1]), max(box[2], ocr_box[2]), max(box[3], ocr_box[3])]
    return box
