"""视频字幕翻译工具 · 本地服务入口。

    python app.py        然后打开 http://localhost:8000
"""
from __future__ import annotations

import base64
import io
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from fastapi import Body, FastAPI, File, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, PlainTextResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from core import detect, jobs, project as proj, render, style, subtitles, transcribe, translate, video  # noqa: E402

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="字幕工作室")


def _load(name: str) -> dict:
    try:
        return proj.load(name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "项目不存在")


def _default_placement(bbox, height: int) -> str:
    return "above" if bbox and bbox[3] > height * 0.7 else "below"


# ---------- 项目 ----------

@app.get("/api/projects")
def list_projects():
    return proj.list_projects()


@app.post("/api/projects")
async def upload(file: UploadFile = File(...)):
    base = proj.safe_name(file.filename or "video")
    name, n = base, 1
    while proj.project_dir(name).exists():
        n += 1
        name = f"{base}_{n}"
    d = proj.project_dir(name)
    d.mkdir(parents=True)
    ext = Path(file.filename or "in.mp4").suffix.lower() or ".mp4"
    src = d / f"in{ext}"
    with open(src, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        meta = video.probe(src)
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(400, f"无法读取视频：{e}")
    data = {"video": {"path": src.name, **meta}, "topic": name, "description": "",
            "cues": [], "logos": [], "glossary": {}}
    proj.save(name, data)
    job = _detect_job(name, auto_transcribe=True)
    return {"name": name, "project": data, "job": job}


@app.get("/api/projects/{name}")
def get_project(name: str):
    return {"project": _load(name), "jobs": jobs.active(name)}


@app.put("/api/projects/{name}")
def put_project(name: str, data: dict = Body(...)):
    old = _load(name)
    data["video"] = old["video"]  # 视频信息不允许前端改
    proj.save(name, data)
    return {"ok": True}


@app.get("/api/projects/{name}/video")
def get_video(name: str):
    p = _load(name)
    return FileResponse(proj.project_dir(name) / p["video"]["path"])


@app.get("/api/projects/{name}/exports/{file}")
def get_export(name: str, file: str):
    path = (proj.project_dir(name) / "exports" / file).resolve()
    if path.parent != (proj.project_dir(name) / "exports").resolve() or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=file)


@app.get("/api/projects/{name}/exports")
def list_exports(name: str):
    d = proj.project_dir(name) / "exports"
    return sorted((p.name for p in d.glob("*.mp4")), reverse=True) if d.exists() else []


@app.post("/api/projects/{name}/clean")
def clean_cache(name: str):
    shutil.rmtree(proj.project_dir(name) / "cache", ignore_errors=True)
    return {"ok": True}


# ---------- 任务 ----------

def _detect_job(name: str, auto_transcribe: bool = False) -> dict:
    def run(progress):
        p = proj.load(name)
        v = p["video"]
        scale = 0.6 if auto_transcribe else 1.0   # 可能接着转写，进度条留出余量
        res = detect.detect(str(proj.project_dir(name) / v["path"]), v["width"], v["height"], v["fps"],
                            lambda f, m: progress(f * scale, m))
        cues = [proj.new_cue(**c, placement=_default_placement(c["source_bbox"], v["height"])) for c in res["cues"]]
        mode = "burned"
        if not cues and auto_transcribe and v.get("has_audio"):
            # 画面里没有字幕：自动改走语音转写
            try:
                cues = _transcribe_cues(name, lambda f, m: progress(0.6 + 0.4 * f, m))
                mode = "speech"
            except RuntimeError as e:  # 没装转写引擎：保留空表，把原因告诉前端
                return {"count": 0, "mode": "none", "message": str(e)}
        p = proj.load(name)  # 期间可能被改过，重新读
        p.update(cues=proj.renumber(cues), logos=res["logos"], source_mode=mode)
        proj.save(name, p)
        return {"count": len(cues), "mode": mode}
    return jobs.submit("detect", name, run)


def _transcribe_cues(name: str, progress, vocals: bool = False) -> list[dict]:
    p = proj.load(name)
    v = p["video"]
    res = transcribe.transcribe(proj.project_dir(name) / v["path"], v["duration"], progress, vocals=vocals)
    out = []
    for c in res["cues"]:
        cue = proj.new_cue(start=c["start"], end=c["end"], source_text=c["text"], source_bbox=None,
                           kind="caption", placement="below")
        if c.get("lyric_suspect"):
            cue["note"] = "疑似歌词，请确认类型"
        out.append(cue)
    return out


@app.post("/api/projects/{name}/transcribe")
def start_transcribe(name: str, vocals: bool = False):
    _load(name)

    def run(progress):
        cues = _transcribe_cues(name, progress, vocals)
        p = proj.load(name)
        p.update(cues=proj.renumber(cues), source_mode="speech")
        proj.save(name, p)
        return {"count": len(cues), "mode": "speech"}
    return jobs.submit("transcribe", name, run)


@app.post("/api/projects/{name}/subtitles.srt")
async def import_srt(name: str, file: UploadFile = File(...)):
    p = _load(name)
    text = (await file.read()).decode("utf-8-sig", errors="replace")
    items = subtitles.parse_srt(text)
    if not items:
        raise HTTPException(400, "SRT 里没有读到字幕")
    # 导入的文字当作中文（已经翻好的字幕）；原文留空
    p["cues"] = proj.renumber([proj.new_cue(start=i["start"], end=i["end"], source_text="", source_bbox=None,
                                            lines=i["lines"]) for i in items])
    proj.save(name, p)
    return {"count": len(items)}


@app.post("/api/projects/{name}/detect")
def start_detect(name: str):
    _load(name)
    return _detect_job(name)


@app.post("/api/projects/{name}/translate")
def start_translate(name: str):
    _load(name)

    def run(progress):
        p = proj.load(name)
        progress(0.1, "Claude 翻译中")
        cues = translate.translate(p["cues"], p.get("description", ""), p.get("glossary"))
        p = proj.load(name)
        p["cues"] = proj.renumber(cues)
        proj.save(name, p)
        return {"count": len(cues)}
    return jobs.submit("translate", name, run)


@app.post("/api/projects/{name}/cues/{cue_id}/alternatives")
def cue_alternatives(name: str, cue_id: str, n: int = 3):
    p = _load(name)
    cue = next((c for c in p["cues"] if c["id"] == cue_id), None)
    if not cue:
        raise HTTPException(404, "没有这条字幕")
    try:
        return translate.alternatives(cue, p["cues"], max(1, min(n, 5)), p.get("description", ""), p.get("glossary"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"翻译失败：{e}")


@app.post("/api/projects/{name}/export")
def start_export(name: str):
    _load(name)

    def run(progress):
        return render.export(proj.load(name), proj.project_dir(name), progress)
    return jobs.submit("export", name, run)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404)
    return job


# ---------- 样式与预览 ----------

@app.get("/api/presets")
def get_presets():
    return style.load_presets()


@app.post("/api/presets/{preset_name}")
def save_preset(preset_name: str, preset: dict = Body(...)):
    style.save_preset(preset_name, preset)
    return style.load_presets()


@app.post("/api/projects/{name}/preview")
def preview(name: str, cue: dict = Body(...)):
    """渲染单条字幕层，前端在 Canvas 上按 (x, y) 叠加——和导出用的是同一张图。"""
    v = _load(name)["video"]
    r = style.render(cue, style.load_presets(), v["width"], v["height"])
    png = None
    if r["image"] is not None:
        buf = io.BytesIO()
        r["image"].save(buf, "PNG")
        png = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"png": png, "x": r["x"], "y": r["y"], "warnings": r["warnings"]}


# ---------- 台词表导出 ----------

@app.get("/api/projects/{name}/subtitles.srt", response_class=PlainTextResponse)
def export_srt(name: str):
    return PlainTextResponse(subtitles.to_srt(_load(name)["cues"]), headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{name}.srt"})


@app.get("/api/projects/{name}/subtitles.md", response_class=PlainTextResponse)
def export_md(name: str):
    return PlainTextResponse(subtitles.to_markdown(_load(name)["cues"]), headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{name}.md"})


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("提示：未设置 ANTHROPIC_API_KEY（.env），翻译功能将不可用。")
    print("打开 http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
