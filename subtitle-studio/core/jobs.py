"""后台任务队列：长任务（识别、翻译、压制）排队在单个工作线程里跑，前端轮询进度。"""
from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from typing import Any, Callable

_jobs: dict[str, dict] = {}
_queue: "queue.Queue[tuple[str, Callable]]" = queue.Queue()
_lock = threading.Lock()


def _worker():
    while True:
        job_id, fn = _queue.get()
        job = _jobs[job_id]
        job.update(status="running", started=time.time())

        def progress(frac: float, msg: str = ""):
            job.update(progress=round(max(0.0, min(1.0, frac)), 4), message=msg)

        try:
            job["result"] = fn(progress)
            job.update(status="done", progress=1.0)
        except Exception as e:  # noqa: BLE001 - 错误要回给前端显示
            traceback.print_exc()
            job.update(status="error", error=str(e))
        finally:
            job["finished"] = time.time()


_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()


def submit(kind: str, project: str, fn: Callable[[Callable[[float, str], None]], Any]) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "kind": kind, "project": project, "status": "queued",
           "progress": 0.0, "message": "排队中", "result": None, "error": None, "created": time.time()}
    with _lock:
        _jobs[job_id] = job
    _queue.put((job_id, fn))
    return job


def get(job_id: str) -> dict | None:
    job = _jobs.get(job_id)
    if job and job["status"] == "running" and job["progress"] > 0.02:
        elapsed = time.time() - job["started"]
        job["eta"] = round(elapsed / job["progress"] * (1 - job["progress"]), 1)
    return job


def active(project: str) -> list[dict]:
    return [j for j in _jobs.values() if j["project"] == project and j["status"] in ("queued", "running")]
