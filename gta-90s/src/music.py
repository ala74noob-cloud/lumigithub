# -*- coding: utf-8 -*-
"""Lay one music track per era segment under the narration and re-mux the final video.

usage: python3 src/music.py build/music/plan.json
plan.json: {"gta1": {"file": "...", "offset": null|seconds, "gain_db": 0}, ...}
  offset null -> auto: skip a quiet intro and start on a strong onset.
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "build", "timeline.json"), encoding="utf-8"))
SR = 48000
SEG = {s["id"]: s for s in TL["segments"]}
OUT = os.path.join(ROOT, "out")
NAME = "GTA编年史_90秒"

TARGET_LUFS = -23.0      # music level in the gaps (before ducking)
DUCK_DB = -9.0           # extra attenuation while the narrator speaks
FADE_IN, FADE_OUT, TAIL = 0.10, 0.45, 0.35


def load(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def kweight(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621]
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    y = kweight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk:
        return -70.0
    ms = np.array([np.mean(np.sum(y[i:i + blk] ** 2, axis=1)) for i in range(0, len(y) - blk, hop)])
    l = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[l > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    g2 = ms[(l > -70) & (l > rel)]
    return float(-0.691 + 10 * np.log10(np.mean(g2) + 1e-12))


def auto_offset(x, seg_len):
    mono = x.mean(axis=1)
    y = kweight(mono[:, None])[:, 0]
    hop = int(0.05 * SR)
    n = len(y) // hop
    env = 10 * np.log10(np.array([np.mean(y[i * hop:(i + 1) * hop] ** 2) for i in range(n)]) + 1e-12)
    sm = np.convolve(np.pad(env, (4, 3), mode="edge"), np.ones(8) / 8, mode="valid")  # edge-pad: zero-pad would read as 0 dB
    limit = max(1, min(n, int(min(90.0, len(mono) / SR - seg_len - 1) * SR / hop)))
    ref = np.percentile(sm[:max(limit, 20)], 85)
    start = next((i for i in range(limit) if sm[i] > ref - 5), 0)
    # snap to the strongest onset within +-0.6 s
    flux = np.maximum(0, np.diff(sm, prepend=sm[0]))
    w = int(0.6 * SR / hop)
    lo, hi = max(0, start - w), min(len(flux), start + w)
    best = lo + int(np.argmax(flux[lo:hi])) if hi > lo else start
    return max(0.0, best * hop / SR - 0.05)


def voice_env(voice):
    act = (np.abs(voice) > 0.015).astype(float)
    k = int(0.12 * SR)
    act = np.convolve(act, np.ones(k) / k, mode="same") > 0.05
    a_att, a_rel = np.exp(-1 / (0.04 * SR)), np.exp(-1 / (0.35 * SR))
    env = signal.lfilter([1 - a_rel], [1, -a_rel], act.astype(float))
    env = np.maximum(env, signal.lfilter([1 - a_att], [1, -a_att], act.astype(float)))
    return np.clip(env * 1.4, 0, 1)


def main(plan_path):
    plan = json.load(open(plan_path, encoding="utf-8"))
    voice, _ = sf.read(os.path.join(ROOT, "build", "audio", "voice.wav"))
    sfx, _ = sf.read(os.path.join(ROOT, "build", "audio", "sfx.wav"))
    N = len(voice)
    music = np.zeros((N, 2))
    report = []
    for sid, cfg in plan.items():
        s = SEG[sid]
        seg_len = s["end"] - s["start"]
        x = load(cfg["file"])
        off = cfg.get("offset")
        off = auto_offset(x, seg_len) if off is None else float(off)
        L = int((seg_len + TAIL + 0.05) * SR)
        clip = x[int(off * SR): int(off * SR) + L].copy()
        if len(clip) < L:
            clip = np.concatenate([clip, np.zeros((L - len(clip), 2))])
        gain = TARGET_LUFS - lufs(clip) + cfg.get("gain_db", 0.0)
        clip *= 10 ** (gain / 20)
        fi, fo = int(FADE_IN * SR), int(FADE_OUT * SR)
        clip[:fi] *= np.linspace(0, 1, fi)[:, None]
        clip[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
        o = int((s["start"] - 0.05) * SR)
        e = min(N, o + L)
        music[o:e] += clip[: e - o]
        report.append({"seg": sid, "file": os.path.basename(cfg["file"]), "title": cfg.get("title", ""),
                       "offset": round(off, 2), "start": s["start"], "end": s["end"], "gain_db": round(gain, 1)})
    duck = 1 - (1 - 10 ** (DUCK_DB / 20)) * voice_env(voice[:, 0])
    music *= duck[:, None]
    mix = voice + sfx + music
    os.makedirs(os.path.join(ROOT, "build", "music"), exist_ok=True)
    raw = os.path.join(ROOT, "build", "music", "mix_music.wav")
    sf.write(raw, mix, SR, subtype="FLOAT")
    os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)
    sf.write(os.path.join(ROOT, "build", "music", "music.wav"), music, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(ROOT, "build", "music", "music.wav"),
                    "-c:a", "flac", os.path.join(OUT, "stems", "music.flac")], check=True)

    # loudness: pre-limit peaks, then linear loudnorm to -16 LUFS / -1.5 dBTP
    pre = "alimiter=limit=0.45:attack=1:release=60:level=disabled"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", raw, "-af",
                        pre + ",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    norm = os.path.join(ROOT, "build", "music", "mix_music_norm.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", pre + "," + ln, "-ar", str(SR),
                    "-c:a", "pcm_s24le", norm], check=True)
    src_video = os.path.join(OUT, NAME + ".mp4")
    final = os.path.join(OUT, NAME + "_配乐版.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src_video, "-i", norm, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=90秒看完GTA 1-6代发展史（配乐版）", final], check=True)
    json.dump(report, open(os.path.join(ROOT, "build", "music", "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for row in report:
        print(row)
    print("->", final)


if __name__ == "__main__":
    main(sys.argv[1])
