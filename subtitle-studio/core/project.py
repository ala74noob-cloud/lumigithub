"""project.json 读写。每个视频一个文件夹，project.json 是唯一的数据源。"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = Path(os.environ.get("SUBTITLE_STUDIO_PROJECTS", ROOT / "projects"))

_lock = threading.Lock()

CUE_DEFAULTS = {
    "kind": "caption",
    "fade": {"in": None, "out": None, "curve": None},
    "lines": [],
    "placement": "below",
    "style": "gold",
    "style_override": {},
    "cover": "none",
    "inpaint": False,
    "note": "",
}


def safe_name(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|\s]+", "_", Path(name).stem).strip("._")
    return name or "video"


def project_dir(name: str) -> Path:
    d = (PROJECTS_DIR / name).resolve()
    if PROJECTS_DIR.resolve() not in d.parents:
        raise ValueError("非法项目名")
    return d


def load(name: str) -> dict:
    with open(project_dir(name) / "project.json", encoding="utf-8") as f:
        return json.load(f)


def save(name: str, data: dict) -> None:
    d = project_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "project.json.tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, d / "project.json")


def list_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(p.parent.name for p in PROJECTS_DIR.glob("*/project.json"))


def new_cue(**fields) -> dict:
    cue = json.loads(json.dumps(CUE_DEFAULTS))
    cue.update(fields)
    return cue


def renumber(cues: list[dict]) -> list[dict]:
    cues.sort(key=lambda c: (c["start"], c["end"]))
    for i, c in enumerate(cues, 1):
        c["id"] = f"c{i:02d}"
    return cues
