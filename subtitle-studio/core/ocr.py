"""OCR 引擎封装：PaddleOCR（首选）→ RapidOCR（PaddleOCR 模型的 ONNX 版）→ EasyOCR。

统一返回 [{"box": [x0, y0, x1, y1], "text": str, "score": float}, ...]。
"""
from __future__ import annotations

import os
import threading

import numpy as np

_engine = None
_engine_name = None
_lock = threading.Lock()


def _box(points) -> list[int]:
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    return [int(pts[:, 0].min()), int(pts[:, 1].min()), int(pts[:, 0].max()), int(pts[:, 1].max())]


def _load():
    global _engine, _engine_name
    wanted = os.environ.get("OCR_ENGINE", "").lower()
    order = [wanted] if wanted else ["paddle", "rapid", "easy"]
    errors = []
    for name in order:
        try:
            if name == "paddle":
                from paddleocr import PaddleOCR
                _engine = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            elif name == "rapid":
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
            elif name == "easy":
                import easyocr
                _engine = easyocr.Reader(["en", "id"], verbose=False)
            else:
                continue
            _engine_name = name
            return
        except Exception as e:  # noqa: BLE001 - 尝试下一个引擎
            errors.append(f"{name}: {e}")
    raise RuntimeError("没有可用的 OCR 引擎，请安装 paddleocr 或 rapidocr-onnxruntime。\n" + "\n".join(errors))


def engine_name() -> str:
    with _lock:
        if _engine is None:
            _load()
    return _engine_name


def read(img: np.ndarray, min_score: float = 0.5) -> list[dict]:
    """img 为 BGR。"""
    with _lock:
        if _engine is None:
            _load()
        if _engine_name == "paddle":
            raw = _engine.ocr(img, cls=False) or []
            items = [(r[0], r[1][0], r[1][1]) for page in raw if page for r in page]
        elif _engine_name == "rapid":
            raw, _ = _engine(img)
            items = [(r[0], r[1], r[2]) for r in (raw or [])]
        else:
            items = _engine.readtext(img[:, :, ::-1])
    out = []
    for pts, text, score in items:
        text = str(text).strip()
        if text and float(score) >= min_score:
            out.append({"box": _box(pts), "text": text, "score": float(score)})
    return out


def join_lines(results: list[dict]) -> str:
    """把一个区域内的 OCR 结果按行（从上到下、从左到右）拼成文字。"""
    if not results:
        return ""
    rs = sorted(results, key=lambda r: (r["box"][1] + r["box"][3]) / 2)
    lines: list[list[dict]] = []
    for r in rs:
        cy = (r["box"][1] + r["box"][3]) / 2
        h = r["box"][3] - r["box"][1]
        if lines:
            last = lines[-1][-1]
            lcy = (last["box"][1] + last["box"][3]) / 2
            if abs(cy - lcy) < max(h, last["box"][3] - last["box"][1]) * 0.5:
                lines[-1].append(r)
                continue
        lines.append([r])
    return "\n".join(" ".join(x["text"] for x in sorted(line, key=lambda r: r["box"][0])) for line in lines)
