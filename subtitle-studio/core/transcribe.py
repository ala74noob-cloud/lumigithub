"""语音转写（指南第 3 部分 B 路径）：视频里没有烧录字幕时，用 Whisper 听写出带词级时间戳的台词。

引擎优先级：
  - mlx-whisper：Apple Silicon（M1–M4）用 GPU 跑，Mac 上最快
  - faster-whisper：其他电脑（N 卡走 CUDA，否则 CPU int8）
可用环境变量 WHISPER_ENGINE=mlx|faster 和 WHISPER_MODEL 指定。
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

Progress = Callable[[float, str], None]

MLX_MODEL = "mlx-community/whisper-large-v3-turbo"
FASTER_MODEL = "large-v3"

PAUSE_SPLIT = 0.45     # 词间停顿超过这个秒数就断句
MAX_DUR = 5.0          # 每条最长 5 秒
MIN_DUR = 1.2          # 每条最短 1.2 秒
MAX_CHARS = 42         # 原文一条最多约 42 个字母（两行英文）
SENTENCE_END = re.compile(r"[.!?。！？…]$")


def _apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def engine_name() -> str:
    wanted = os.environ.get("WHISPER_ENGINE", "").lower()
    if wanted in ("mlx", "faster"):
        return wanted
    if _apple_silicon():
        try:
            import mlx_whisper  # noqa: F401
            return "mlx"
        except ImportError:
            pass
    try:
        import faster_whisper  # noqa: F401
        return "faster"
    except ImportError:
        pass
    hint = "pip install mlx-whisper" if _apple_silicon() else "pip install faster-whisper"
    raise RuntimeError(f"没有可用的语音转写引擎，请先运行：{hint}")


def extract_audio(video: Path, out: Path) -> Path:
    """抽成 16kHz 单声道 wav（Whisper 的输入格式）。"""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(out)],
                   check=True)
    return out


def separate_vocals(wav: Path, work: Path) -> Path:
    """背景音乐很响时（演出现场）先用 demucs 分离人声。没装 demucs 就原样返回。"""
    try:
        import demucs  # noqa: F401
    except ImportError:
        return wav
    subprocess.run(["python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", str(work), str(wav)],
                   check=True)
    hits = list(work.glob(f"htdemucs/{wav.stem}/vocals.wav"))
    return hits[0] if hits else wav


def _words_mlx(wav: Path, language: str | None) -> tuple[list[dict], str]:
    import mlx_whisper
    res = mlx_whisper.transcribe(str(wav), path_or_hf_repo=os.environ.get("WHISPER_MODEL", MLX_MODEL),
                                 word_timestamps=True, language=language,
                                 condition_on_previous_text=False)
    words = [{"word": w["word"], "start": float(w["start"]), "end": float(w["end"]),
              "prob": float(w.get("probability", 1.0))}
             for seg in res.get("segments", []) for w in seg.get("words", [])]
    return words, res.get("language", "")


def _words_faster(wav: Path, language: str | None, progress: Progress, duration: float) -> tuple[list[dict], str]:
    from faster_whisper import WhisperModel
    try:
        import torch
        cuda = torch.cuda.is_available()
    except ImportError:
        cuda = False
    model = WhisperModel(os.environ.get("WHISPER_MODEL", FASTER_MODEL),
                         device="cuda" if cuda else "cpu", compute_type="float16" if cuda else "int8")
    segments, info = model.transcribe(str(wav), word_timestamps=True, language=language, vad_filter=True,
                                      condition_on_previous_text=False)
    words = []
    for seg in segments:  # 生成器：边转写边报告进度
        words += [{"word": w.word, "start": float(w.start), "end": float(w.end), "prob": float(w.probability)}
                  for w in (seg.words or [])]
        progress(0.2 + 0.7 * min(1.0, seg.end / max(duration, 0.1)), f"转写中 {seg.end:.0f}/{duration:.0f} 秒")
    return words, info.language


def group_words(words: list[dict]) -> list[dict]:
    """按停顿、句末标点和长度把词拼成字幕条。"""
    cues: list[dict] = []
    cur: list[dict] = []

    def flush():
        if cur:
            text = "".join(w["word"] for w in cur).strip()
            if text:
                cues.append({"start": round(cur[0]["start"], 3), "end": round(cur[-1]["end"], 3), "text": text})
        cur.clear()

    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            text_len = len("".join(x["word"] for x in cur).strip())
            too_long = w["end"] - cur[0]["start"] > MAX_DUR or text_len + len(w["word"]) > MAX_CHARS
            sentence_done = SENTENCE_END.search(cur[-1]["word"].strip()) and cur[-1]["end"] - cur[0]["start"] >= MIN_DUR
            if gap > PAUSE_SPLIT or too_long or sentence_done:
                flush()
        cur.append(w)
    flush()
    # 太短的条并到相邻条（间隔很小时），否则留给翻译后的最短时长规则处理
    merged: list[dict] = []
    for c in cues:
        if merged and c["end"] - c["start"] < MIN_DUR and c["start"] - merged[-1]["end"] < PAUSE_SPLIT \
                and c["end"] - merged[-1]["start"] <= MAX_DUR:
            merged[-1]["end"] = c["end"]
            merged[-1]["text"] += " " + c["text"]
        else:
            merged.append(dict(c))
    return merged


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-zÀ-ɏ]+", " ", text.lower()).strip()


def mark_lyric_suspects(cues: list[dict]) -> None:
    """简单启发式：同一句出现 ≥2 次（副歌重复）或押韵的连续短句，标为“疑似歌词”，让用户确认。"""
    counts: dict[str, int] = {}
    for c in cues:
        counts[_norm(c["text"])] = counts.get(_norm(c["text"]), 0) + 1
    for i, c in enumerate(cues):
        n = _norm(c["text"])
        repeated = len(n) > 8 and counts[n] >= 2
        rhyme = False
        if i > 0:
            a, b = _norm(cues[i - 1]["text"]).split(), n.split()
            rhyme = bool(a and b and len(a[-1]) > 2 and a[-1] != b[-1] and a[-1][-3:] == b[-1][-3:])
        if repeated or rhyme:
            c["lyric_suspect"] = True


def transcribe(video: Path, duration: float, progress: Progress | None = None,
               language: str | None = None, vocals: bool = False) -> dict:
    progress = progress or (lambda f, m: None)
    engine = engine_name()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        progress(0.02, "抽取音频")
        wav = extract_audio(video, tmp / "audio.wav")
        if vocals:
            progress(0.06, "分离人声（demucs）")
            wav = separate_vocals(wav, tmp)
        progress(0.15, "加载语音模型（首次会下载，约 1.5GB）")
        if engine == "mlx":
            words, lang = _words_mlx(wav, language)
        else:
            words, lang = _words_faster(wav, language, progress, duration)
    cues = group_words(words)
    mark_lyric_suspects(cues)
    progress(1.0, f"转写完成，共 {len(cues)} 条")
    return {"cues": cues, "language": lang, "engine": engine}
