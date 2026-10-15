"""语音转写：引擎输出用替身（测试环境下载不了 Whisper 模型），检查断句、自动切换、歌词提示和 SRT 导入。"""
from __future__ import annotations

import time

import pytest

from core import transcribe
from tests import make_sample
from tests.test_pipeline import _wait, client  # noqa: F401  (共用 fixture)


def W(word, s, e):
    return {"word": word, "start": s, "end": e, "prob": 0.9}


WORDS = [W(" Hey", 0.30, 0.50), W(" guys,", 0.50, 0.80), W(" welcome", 0.85, 1.20), W(" to", 1.20, 1.30),
         W(" Buenos", 1.30, 1.60), W(" Aires.", 1.60, 2.10),
         W(" Tonight", 3.00, 3.40), W(" is", 3.40, 3.50), W(" gonna", 3.50, 3.80), W(" be", 3.80, 3.90),
         W(" crazy", 3.90, 4.40)]


def test_group_words_splits_on_sentence_end_and_pause():
    cues = transcribe.group_words(WORDS)
    assert [c["text"] for c in cues] == ["Hey guys, welcome to Buenos Aires.", "Tonight is gonna be crazy"]
    assert (cues[0]["start"], cues[0]["end"]) == (0.3, 2.1)
    assert (cues[1]["start"], cues[1]["end"]) == (3.0, 4.4)


def test_group_words_caps_duration():
    words = [W(f" w{i}", i * 0.3, i * 0.3 + 0.28) for i in range(40)]   # 12 秒不停顿
    cues = transcribe.group_words(words)
    assert all(c["end"] - c["start"] <= transcribe.MAX_DUR + 1e-6 for c in cues)
    assert all(len(c["text"]) <= transcribe.MAX_CHARS for c in cues)


def test_lyric_suspects_repeated_chorus():
    cues = [{"text": "I wanna run away with you"}, {"text": "hello there"}, {"text": "I wanna run away with you"}]
    transcribe.mark_lyric_suspects(cues)
    assert cues[0].get("lyric_suspect") and cues[2].get("lyric_suspect") and not cues[1].get("lyric_suspect")


@pytest.fixture(scope="module")
def speech_video(tmp_path_factory):
    p = tmp_path_factory.mktemp("speech") / "interview.mp4"
    make_sample.main(str(p), cues=[], logo=None)   # 画面里没有任何字幕
    return p


def test_upload_without_burned_subs_falls_back_to_speech(client, speech_video, monkeypatch):  # noqa: F811
    monkeypatch.setattr(transcribe, "engine_name", lambda: "faster")
    monkeypatch.setattr(transcribe, "_words_faster", lambda wav, lang, progress, dur: (WORDS, "en"))
    with open(speech_video, "rb") as f:
        r = client.post("/api/projects", files={"file": ("interview.mp4", f, "video/mp4")})
    name = r.json()["name"]
    job = _wait(client, r.json()["job"])
    assert job["result"] == {"count": 2, "mode": "speech"}
    p = client.get(f"/api/projects/{name}").json()["project"]
    assert p["source_mode"] == "speech"
    assert [c["source_text"] for c in p["cues"]] == ["Hey guys, welcome to Buenos Aires.", "Tonight is gonna be crazy"]
    assert all(c["source_bbox"] is None for c in p["cues"])

    # 没有原文位置时，中文放在底部安全区上方
    cue = dict(p["cues"][0], lines=["哈喽大家", "欢迎来到布宜诺斯艾利斯"])
    prev = client.post(f"/api/projects/{name}/preview", json=cue).json()
    assert prev["png"] and 1280 * 0.55 < prev["y"] < 1280 * 0.8

    # 手动“语音转写”按钮
    job = _wait(client, client.post(f"/api/projects/{name}/transcribe").json())
    assert job["result"]["count"] == 2


def test_no_engine_installed_reports_hint(client, speech_video, monkeypatch):  # noqa: F811
    def missing():
        raise RuntimeError("没有可用的语音转写引擎，请先运行：pip install mlx-whisper")
    monkeypatch.setattr(transcribe, "engine_name", missing)
    with open(speech_video, "rb") as f:
        r = client.post("/api/projects", files={"file": ("interview.mp4", f, "video/mp4")})
    job = _wait(client, r.json()["job"])
    assert job["result"]["mode"] == "none" and "mlx-whisper" in job["result"]["message"]


def test_srt_import(client, speech_video):  # noqa: F811
    name = client.get("/api/projects").json()[0]
    srt = "1\n00:00:00,500 --> 00:00:02,000\n哈喽大家\n欢迎来到布宜诺斯艾利斯\n\n2\n00:00:03,000 --> 00:00:04,400\n今晚要炸了🔥\n"
    r = client.post(f"/api/projects/{name}/subtitles.srt", files={"file": ("a.srt", srt.encode(), "text/plain")})
    assert r.json() == {"count": 2}
    cues = client.get(f"/api/projects/{name}").json()["project"]["cues"]
    assert cues[0]["lines"] == ["哈喽大家", "欢迎来到布宜诺斯艾利斯"] and cues[1]["end"] == 4.4
