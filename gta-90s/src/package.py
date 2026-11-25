# -*- coding: utf-8 -*-
"""Mux + deliverables: final mp4 (with chapters), stems, music cue sheet, SRT."""
import json, os, re, subprocess, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "build", "timeline.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "out")
os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)
VIDEO = os.path.join(ROOT, "build", "video", "video.mp4")
AUD = os.path.join(ROOT, "build", "audio")
NAME = "GTA编年史_90秒"


def ts(t, sep="."):
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}" if sep == "." else f"{int(m):02d}:{int(s):02d}"


def srt_ts(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


# ---------------- loudness: two-pass loudnorm on the mix (target -15 LUFS, -1.5 dBTP)
mix = os.path.join(AUD, "mix.wav")
pre = "alimiter=limit=0.45:attack=1:release=60:level=disabled"
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mix, "-af",
                    pre + ",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True)
meas = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
ln = ("loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
      f"measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:"
      f"measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}")
mix_norm = os.path.join(AUD, "mix_norm.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mix, "-af", pre + "," + ln, "-ar", "48000", "-c:a", "pcm_s24le", mix_norm], check=True)

# ---------------- chapters metadata
labels = {"hook": "开场：90秒看完GTA", "gta1": "1997 GTA", "gta2": "1999 GTA 2", "gta3": "2001 GTA III",
          "vc": "2002 罪恶都市", "sa": "2004 圣安地列斯", "gta4": "2008 GTA IV", "gta5": "2013 GTA V",
          "gta6": "2026 GTA VI", "outro": "结尾"}
meta = os.path.join(ROOT, "build", "chapters.txt")
with open(meta, "w", encoding="utf-8") as f:
    f.write(";FFMETADATA1\ntitle=90秒看完GTA 1-6代发展史\n")
    for s in TL["segments"]:
        f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(s['start']*1000)}\nEND={int(s['end']*1000)}\ntitle={labels[s['id']]}\n")

final = os.path.join(OUT, NAME + ".mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", VIDEO, "-i", mix_norm,
                "-map", "0:v", "-map", "1:a", "-metadata", "title=90秒看完GTA 1-6代发展史",
                "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "9M", "-bufsize", "18M",
                "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "256k",
                "-shortest", "-movflags", "+faststart", final], check=True)

# stems (same timeline, original relative levels: voice + sfx = mix before loudness normalisation)
for s in ("voice", "sfx"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(AUD, s + ".wav"), "-c:a", "flac",
                    os.path.join(OUT, "stems", f"{s}.flac")], check=True)


# ---------------- SRT (full narration, numbers as digits)
SUB = [("一九九七年", "1997年"), ("一九九九年", "1999年"), ("二零零一年", "2001年"), ("二零零四年", "2004年"),
       ("二零零八年", "2008年"), ("二零一三年", "2013年"), ("二零二六年十一月十九日", "2026年11月19日"),
       ("二十九年后", "29年后"), ("三十七点九亿", "37.9亿"), ("九十秒", "90秒"), ("GTA一到六代", "GTA 1-6代"),
       ("十三年", "13年"), ("十七岁", "17岁"), ("二十四小时", "24小时"), ("九千万", "9000万"),
       ("两亿三千五百万", "2.35亿"), ("十亿", "10亿"), ("五亿", "5亿"), ("三天", "3天"), ("八十年代", "80年代"),
       ("九一一", "9·11"), ("GTA3", "GTA3"), ("bug", "BUG")]
with open(os.path.join(OUT, NAME + "_字幕.srt"), "w", encoding="utf-8") as f:
    for i, l in enumerate(TL["lines"], 1):
        txt = l["tts"]
        for a, b in SUB:
            txt = txt.replace(a, b)
        txt = txt.rstrip("，；、")
        f.write(f"{i}\n{srt_ts(l['start'])} --> {srt_ts(l['end'] + 0.15)}\n{txt}\n\n")

# ---------------- music cue sheet
cues = [s for s in TL["segments"]]
rows = []
for s in cues:
    rows.append((labels[s["id"]], s["start"], s["end"]))
with open(os.path.join(OUT, NAME + "_音乐打点.txt"), "w", encoding="utf-8") as f:
    f.write("90秒看完GTA 1-6代 —— 音乐打点表（时间均以成片为准，30fps）\n")
    f.write("=" * 58 + "\n\n")
    f.write("段落                    入点        出点        时长     帧号(入→出)\n")
    for name, a, b in rows:
        f.write(f"{name:<14s}\t{ts(a)}\t{ts(b)}\t{b-a:5.2f}s\t{round(a*30)} → {round(b*30)}\n")
    f.write("\n说明：\n")
    f.write("1. 每代之间的切换点都放了“收音机换台”的调频音效 + 转场呼啸声，\n   音乐直接在入点硬切/0.2秒淡入即可，换台声会自然盖住接缝（很GTA）。\n")
    f.write("2. 解说全程不停，建议音乐压在人声下方约 -18 ~ -22 dB（剪映里大概 15%~25% 音量），\n   人声空档处可以稍微推高。\n")
    f.write("3. 2002 罪恶都市 段的 “八十年代” 落点有一个80年代合成器和弦重音，可以对齐音乐鼓点。\n")
    f.write("4. 2026 GTA VI 段：前 7 秒是“等待/泄露/预告”，画面偏暗；"
            f"{ts(TL['beats']['g6_date'] - 0.55)} 白闪揭晓发售，最适合让音乐的高潮/副歌在这里进。\n")
    f.write("5. 开场 00:00 ~ " + ts(TL['segments'][1]['start']) + " 和结尾目前没有安排音乐，可留空或放主题曲。\n")
    f.write("\n关键节拍（可用于对齐音乐重拍）：\n")
    nice = {"h2_money": "开场 37.9亿", "g1_mad": "GTA1 警察发疯", "g1_born": "GTA诞生", "g2_rockstar": "Rockstar 登场",
            "g3_3d": "GTA3 变3D", "g3_911": "9·11", "vc_80s": "回到80年代", "sa_three": "三座城市", "sa_ao": "热咖啡/成人级",
            "g4_money": "GTA4 5亿美元", "g5_switch": "GTA5 切换主角", "g5_billion": "10亿美元", "g6_leak": "泄露",
            "g6_views": "预告9000万", "g6_release": "GTA6 发售", "g6_money": "37.9亿"}
    for k, v in nice.items():
        f.write(f"  {ts(TL['beats'][k])}  {v}\n")

with open(os.path.join(OUT, NAME + "_markers.csv"), "w", encoding="utf-8") as f:
    f.write("name,start_sec,end_sec,start_tc,end_tc\n")
    for name, a, b in rows:
        f.write(f"{name},{a:.3f},{b:.3f},{ts(a)},{ts(b)}\n")
print("packaged ->", OUT)
print(json.dumps(meas, indent=0)[:300])
