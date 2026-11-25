# -*- coding: utf-8 -*-
"""Synthesize every narration line with edge-tts, trim silence, report durations.

usage: python3 src/tts.py [--voice zh-CN-YunxiNeural] [--rate +8%] [--force]
"""
import argparse, asyncio, json, os, subprocess, sys
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(__file__))
from script import SEGMENTS  # noqa: E402

import edge_tts  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "tts")
SR = 48000


async def synth(text, voice, rate, pitch, path):
    """Returns word boundaries [(start_s, end_s, text), ...] relative to the raw mp3."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    for attempt in range(4):
        try:
            c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=proxy,
                                     boundary="WordBoundary")
            words = []
            with open(path, "wb") as fh:
                async for ch in c.stream():
                    if ch["type"] == "audio":
                        fh.write(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        st = ch["offset"] / 1e7
                        words.append((st, st + ch["duration"] / 1e7, ch["text"]))
            if os.path.getsize(path) > 1000:
                return words
        except Exception as e:  # network hiccup
            print("  retry", attempt, e)
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError("TTS failed: " + text)


def to_wav_trimmed(mp3, wav):
    raw = wav + ".raw.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), raw], check=True)
    x, sr = sf.read(raw)
    os.remove(raw)
    env = np.abs(x)
    thr = 10 ** (-45 / 20)
    idx = np.where(env > thr)[0]
    a = max(0, idx[0] - int(0.03 * sr))
    b = min(len(x), idx[-1] + int(0.06 * sr))
    y = x[a:b].copy()
    to_wav_trimmed.lead = a / sr
    # tiny fades
    f = int(0.008 * sr)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    sf.write(wav, y, sr, subtype="PCM_16")
    return len(y) / sr


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="zh-CN-YunxiNeural")
    ap.add_argument("--rate", default="+8%")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    meta_path = os.path.join(OUT, "durations.json")
    meta = {}
    if os.path.exists(meta_path) and not args.force:
        meta = json.load(open(meta_path))
    total = 0.0
    for seg in SEGMENTS:
        for ln in seg["lines"]:
            key = f'{ln["tts"]}|{args.voice}|{args.rate}|{args.pitch}'
            wav = os.path.join(OUT, ln["id"] + ".wav")
            if meta.get(ln["id"], {}).get("key") != key or not os.path.exists(wav):
                mp3 = os.path.join(OUT, ln["id"] + ".mp3")
                words = await synth(ln["tts"], args.voice, args.rate, args.pitch, mp3)
                d = to_wav_trimmed(mp3, wav)
                lead = to_wav_trimmed.lead
                words = [(round(max(0, a - lead), 3), round(max(0, b - lead), 3), w) for a, b, w in words]
                meta[ln["id"]] = {"key": key, "dur": d, "words": words}
                print(f'{ln["id"]:5s} {d:5.2f}s  {ln["tts"]}')
            total += meta[ln["id"]]["dur"]
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    print(f"speech total: {total:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
