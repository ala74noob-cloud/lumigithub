"""ffprobe 元信息 + 逐帧读取。"""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np


def probe(path: str | Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    fps = float(Fraction(v.get("avg_frame_rate") or v["r_frame_rate"]))
    duration = float(v.get("duration") or info["format"]["duration"])
    rotation = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if abs(rotation) in (90, 270):
        w, h = h, w
    return {
        "width": w, "height": h, "fps": round(fps, 3), "duration": round(duration, 3),
        "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
    }


class FrameReader:
    """顺序读帧（BGR）。frame_time 用帧号 / fps，非整数帧率也按时间换算。"""

    def __init__(self, path: str | Path):
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频：{path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def __iter__(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        i = 0
        while True:
            ok, frame = self.cap.read()
            if not ok:
                break
            yield i, frame
            i += 1

    def read_at(self, index: int) -> np.ndarray | None:
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self.cap.read()
        return frame if ok else None

    def close(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
