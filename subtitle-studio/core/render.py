"""ffmpeg 合成导出（里程碑 1：硬切，overlay enable=between）。

每条字幕渲染一张透明 PNG，按时间段叠到原视频上，音轨原样拷贝。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

from PIL import Image

from . import style

Progress = Callable[[float, str], None]


def next_output_path(out_dir: Path, topic: str) -> Path:
    """<视频主题>_中文字幕_v<版本>.mp4，每次导出版本号 +1，不覆盖旧版。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    versions = [int(m.group(1)) for p in out_dir.glob(f"{topic}_中文字幕_v*.mp4")
                if (m := re.search(r"_v(\d+)\.mp4$", p.name))]
    return out_dir / f"{topic}_中文字幕_v{max(versions, default=0) + 1}.mp4"


def render_layers(project: dict, layer_dir: Path) -> list[dict]:
    """渲染所有字幕层，返回 [{cue_id, path, x, y, start, end, warnings}]。"""
    v = project["video"]
    presets = style.load_presets()
    layer_dir.mkdir(parents=True, exist_ok=True)
    for old in layer_dir.glob("*.png"):
        old.unlink()
    layers = []
    for cue in project["cues"]:
        if cue.get("kind") in ("logo", "lyric") or not cue.get("lines"):
            continue
        r = style.render(cue, presets, v["width"], v["height"])
        if r["image"] is None:
            continue
        path = layer_dir / f"{cue['id']}.png"
        r["image"].save(path)
        layers.append({"cue_id": cue["id"], "path": path, "x": r["x"], "y": r["y"],
                       "start": cue["start"], "end": cue["end"], "warnings": r["warnings"]})
    return layers


def build_command(src: str, layers: list[dict], out: Path, has_audio: bool) -> list[str]:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1", "-i", src]
    for L in layers:
        cmd += ["-i", str(L["path"])]
    if layers:
        parts, last = [], "0:v"
        for i, L in enumerate(layers, 1):
            # 用时间（而不是帧号）控制显示，非整数帧率也准确；区间右端开，避免和下一条重叠一帧
            enable = f"gte(t,{L['start']:.3f})*lt(t,{L['end']:.3f})"
            parts.append(f"[{last}][{i}:v]overlay={L['x']}:{L['y']}:enable='{enable}':format=auto[v{i}]")
            last = f"v{i}"
        cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]"]
    else:
        cmd += ["-map", "0:v"]
    if has_audio:
        cmd += ["-map", "0:a?", "-c:a", "copy"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out)]
    return cmd


def export(project: dict, project_dir: Path, progress: Progress | None = None) -> dict:
    progress = progress or (lambda f, m: None)
    v = project["video"]
    progress(0.02, "渲染字幕层")
    layers = render_layers(project, project_dir / "cache" / "layers")
    topic = project.get("topic") or project_dir.name
    out = next_output_path(project_dir / "exports", topic)
    cmd = build_command(str(project_dir / v["path"]), layers, out, v.get("has_audio", True))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    total_us = max(1.0, v["duration"] * 1e6)
    for line in proc.stdout:
        if line.startswith("out_time_us="):
            try:
                progress(0.05 + 0.9 * min(1.0, int(line.split("=")[1]) / total_us), "压制中")
            except ValueError:
                pass
    err = proc.stderr.read()
    if proc.wait() != 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg 压制失败：{err[-800:]}")
    progress(0.97, "生成检查图")
    check = contact_sheet(out, project, project_dir / "exports" / (out.stem + "_检查图.jpg"))
    warnings = [{"cue_id": L["cue_id"], "message": w} for L in layers for w in L["warnings"]]
    from .video import probe
    got = probe(out)["duration"]
    if abs(got - v["duration"]) > 0.1:
        warnings.append({"cue_id": None, "message": f"导出时长 {got:.2f}s 与原视频 {v['duration']:.2f}s 不一致"})
    progress(1.0, "导出完成")
    return {"file": out.name, "check": check.name if check else None, "warnings": warnings}


def contact_sheet(video: Path, project: dict, out: Path, cols: int = 4) -> Path | None:
    """导出后在每条字幕中点截一帧拼成检查图。"""
    cues = [c for c in project["cues"] if c.get("lines") and c.get("kind") not in ("logo", "lyric")]
    if not cues:
        return None
    thumbs = []
    tmp = out.parent / ".thumb.png"
    for c in cues:
        t = (c["start"] + c["end"]) / 2
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=240:-2", str(tmp)], check=False)
        if tmp.exists():
            thumbs.append(Image.open(tmp).convert("RGB").copy())
    tmp.unlink(missing_ok=True)
    if not thumbs:
        return None
    w, h = thumbs[0].size
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (w * min(cols, len(thumbs)), h * rows), (20, 20, 20))
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out, quality=88)
    return out
