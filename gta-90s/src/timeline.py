# -*- coding: utf-8 -*-
"""Lay narration lines on a single timeline and export it for the renderer + audio mixer.

Writes build/timeline.json and src/timeline.js (window.TL = ...).
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from script import SEGMENTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = json.load(open(os.path.join(ROOT, "build", "tts", "durations.json"), encoding="utf-8"))

LEAD = 0.30          # silence before the very first word
GAP = 0.12           # pause between lines inside a segment
SEG_GAP = 0.42       # pause around a segment transition
TAIL = 1.25          # hold after the last word
PRE = {"g3c": 0.25, "g6d": 0.35, "h3": 0.12}   # extra dramatic pauses before some lines
SEG_GAP_OVERRIDE = {"hook": 0.62}


def build():
    t = LEAD
    segs, lines = [], []
    for si, seg in enumerate(SEGMENTS):
        s_start = None
        for li, ln in enumerate(seg["lines"]):
            if li > 0:
                t += GAP
            t += PRE.get(ln["id"], 0.0)
            m = META[ln["id"]]
            st, en = t, t + m["dur"]
            if s_start is None:
                s_start = st
            words = [[round(st + a, 3), round(st + b, 3), w] for a, b, w in m.get("words", [])]
            lines.append({"id": ln["id"], "seg": seg["id"], "start": round(st, 3), "end": round(en, 3),
                          "card": ln["card"], "big": ln.get("big", 0), "tts": ln["tts"], "words": words})
            t = en
        segs.append({"id": seg["id"], "year": seg["year"], "title": seg["title"],
                     "speech_start": round(s_start, 3), "speech_end": round(t, 3)})
        if si < len(SEGMENTS) - 1:
            t += SEG_GAP_OVERRIDE.get(seg["id"], SEG_GAP)
    total = round(t + TAIL, 3)

    # visual segment boundaries: transition sits in the middle of the gap
    for i, s in enumerate(segs):
        if i == 0:
            s["start"] = 0.0
        else:
            prev = segs[i - 1]
            s["start"] = round((prev["speech_end"] + s["speech_start"]) / 2 + 0.03, 3)
            prev["end"] = s["start"]
    segs[-1]["end"] = total

    def word_time(line_id, needle, which="start"):
        ln = next(l for l in lines if l["id"] == line_id)
        for exact in (True, False):
            for a, b, w in ln["words"]:
                if (w == needle) if exact else (needle in w):
                    return a if which == "start" else b
        raise KeyError(f"{needle} not in {line_id}: {[w for _,_,w in ln['words']]}")

    L = {l["id"]: l for l in lines}
    beats = {
        "h2_money": word_time("h2", "三十七点九亿"),
        "g1_bug": word_time("g1c", "bug"),
        "g1_mad": word_time("g1c", "疯"),
        "g1_ram": word_time("g1c", "猛撞"),
        "g1_born": word_time("g1d", "诞生"),
        "g1_boring": word_time("g1b", "无聊"),
        "g1_cut": word_time("g1b", "砍"),
        "g2_rockstar": word_time("g2a", "Rockstar"),
        "g2_help": word_time("g2b", "帮"),
        "g2_rival": word_time("g2b", "得罪"),
        "g3_3d": word_time("g3a", "D") - 0.25,
        "g3_911": word_time("g3c", "九一一"),
        "g3_delay": word_time("g3d", "延期"),
        "g3_bw": word_time("g3d", "黑白"),
        "vc_80s": word_time("vca", "八十"),
        "vc_talk": word_time("vcb", "说话"),
        "vc_liotta": word_time("vcb", "雷"),
        "sa_three": word_time("saa", "三"),
        "sa_fat": word_time("sab", "胖"),
        "sa_coffee": word_time("sac", "热"),
        "sa_ao": word_time("sac", "成人"),
        "sa_pull": word_time("sac", "下架"),
        "sa_king": word_time("sad", "最多"),
        "g4_real": word_time("g4a", "写实"),
        "g4_money": word_time("g4b", "五亿"),
        "g5_three": word_time("g5a", "三"),
        "g5_switch": word_time("g5a", "切换"),
        "g5_billion": word_time("g5b", "十亿"),
        "g5_record": word_time("g5b", "纪录"),
        "g5_units": word_time("g5c", "两亿"),
        "g6_wait": word_time("g6a", "等待"),
        "g6_hack": word_time("g6b", "黑客"),
        "g6_leak": word_time("g6b", "泄露"),
        "g6_trailer": word_time("g6c", "预告"),
        "g6_views": word_time("g6c", "九千万"),
        "g6_date": word_time("g6d", "二零二六"),
        "g6_release": word_time("g6d", "发售"),
        "g6_money": word_time("g6e", "三十七点九亿"),
        "g6_biggest": word_time("g6e", "最大"),
        "o_fav": L["o2"]["start"],
    }
    beats = {k: round(v, 3) for k, v in beats.items()}

    # music cue sheet: one cue per era segment
    cues = [{"seg": s["id"], "label": f'{s["year"]} {s["title"]}'.strip(), "start": s["start"], "end": s["end"]}
            for s in segs if s["year"]]

    tl = {"fps": 30, "w": 1920, "h": 1080, "total": total, "segments": segs, "lines": lines,
          "beats": beats, "cues": cues}
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    json.dump(tl, open(os.path.join(ROOT, "build", "timeline.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)   # tracked copy for fresh clones / music step
    json.dump(tl, open(os.path.join(ROOT, "data", "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "src", "timeline.js"), "w", encoding="utf-8") as fh:
        fh.write("window.TL = " + json.dumps(tl, ensure_ascii=False) + ";\n")
    return tl


if __name__ == "__main__":
    tl = build()
    print("total", tl["total"])
    for s in tl["segments"]:
        print(f'{s["id"]:6s} {s["start"]:6.2f} -> {s["end"]:6.2f}  ({s["end"]-s["start"]:.2f}s)')
