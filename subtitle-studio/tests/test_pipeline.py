"""端到端：上传 → 识别 → 翻译（替身 Claude）→ 导出，按里程碑 1 的验收标准检查。"""
from __future__ import annotations

import json
import subprocess
import time

import numpy as np
import pytest

from tests import make_sample


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("projects")
    import os
    os.environ["SUBTITLE_STUDIO_PROJECTS"] = str(root)
    import importlib

    from core import project
    importlib.reload(project)
    import app as app_module
    importlib.reload(app_module)
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    p = tmp_path_factory.mktemp("video") / "sample.mp4"
    make_sample.main(str(p))
    return p


def _wait(client, job):
    for _ in range(600):
        j = client.get(f"/api/jobs/{job['id']}").json()
        if j["status"] in ("done", "error"):
            assert j["status"] == "done", j["error"]
            return j
        time.sleep(0.2)
    raise TimeoutError


def _frame(path, t, w=720, h=1280):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def _gold_pixels(img, y0, y1):
    band = img[y0:y1].astype(int)
    r, g, b = band[..., 0], band[..., 1], band[..., 2]
    return int(((r > 220) & (g > 180) & (b < 140)).sum())


def test_end_to_end(client, sample, monkeypatch):
    t0 = time.time()
    with open(sample, "rb") as f:
        r = client.post("/api/projects", files={"file": ("sample.mp4", f, "video/mp4")})
    assert r.status_code == 200, r.text
    name = r.json()["name"]
    _wait(client, r.json()["job"])

    p = client.get(f"/api/projects/{name}").json()["project"]
    fps = make_sample.FPS
    assert [c["source_text"] for c in p["cues"]] == [t for _, _, t in make_sample.CUES]
    assert p["logos"] == ["UPROXX"]
    for cue, (s, e, _) in zip(p["cues"], make_sample.CUES):
        assert abs(cue["start"] - s / fps) <= 1 / fps + 1e-6   # 误差 ≤ 1 帧
        assert abs(cue["end"] - e / fps) <= 1 / fps + 1e-6

    # 替身 Claude：把两条合并成一句（测试合并时间范围）
    from core import translate

    def fake_ask(user, client=None, max_tokens=0):
        ids = [c["id"] for c in json.loads(user)["cues"]]
        return json.dumps([{"merge_ids": ids, "lines": ["当你跟第一个粉丝击了掌", "这只手今晚就不归你了🙏😂"], "note": ""}],
                          ensure_ascii=False)
    monkeypatch.setattr(translate, "_ask", fake_ask)
    _wait(client, client.post(f"/api/projects/{name}/translate").json())
    p = client.get(f"/api/projects/{name}").json()["project"]
    assert len(p["cues"]) == 1
    cue = p["cues"][0]
    assert cue["start"] == pytest.approx(15 / fps, abs=1 / fps) and cue["end"] == pytest.approx(150 / fps, abs=1 / fps)

    prev = client.post(f"/api/projects/{name}/preview", json=cue).json()
    assert prev["png"].startswith("data:image/png") and prev["warnings"] == []

    job = _wait(client, client.post(f"/api/projects/{name}/export").json())
    res = job["result"]
    assert res["file"] == f"{name}_中文字幕_v1.mp4"
    assert res["warnings"] == []
    assert time.time() - t0 < 180   # 验收：上传到导出 ≤ 3 分钟

    out = client.get(f"/api/projects/{name}/exports/{res['file']}")
    assert out.status_code == 200
    from core import project
    out_path = project.project_dir(name) / "exports" / res["file"]
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(out_path)],
                                      capture_output=True, text=True).stdout)
    assert {s["codec_type"] for s in probe["streams"]} == {"video", "audio"}

    # 中文出现/消失时间：字幕段内有金色像素，段外没有
    y0, y1 = prev["y"], prev["y"] + 120
    assert _gold_pixels(_frame(out_path, 1.0), y0, y1) > 500
    assert _gold_pixels(_frame(out_path, 15 / fps + 0.5 / fps), y0, y1) > 500   # 第一帧
    assert _gold_pixels(_frame(out_path, 15 / fps - 1.5 / fps), y0, y1) == 0     # 前一帧
    assert _gold_pixels(_frame(out_path, 150 / fps + 0.5 / fps), y0, y1) == 0
    assert _gold_pixels(_frame(out_path, 5.5), y0, y1) == 0

    # 第二次导出版本号 +1，不覆盖
    job = _wait(client, client.post(f"/api/projects/{name}/export").json())
    assert job["result"]["file"].endswith("_v2.mp4")

    srt = client.get(f"/api/projects/{name}/subtitles.srt").text
    assert "00:00:00,500 --> 00:00:05,000" in srt and "当你跟第一个粉丝击了掌" in srt
    md = client.get(f"/api/projects/{name}/subtitles.md").text
    assert "| 时间 | 原文 | 中文 |" in md
