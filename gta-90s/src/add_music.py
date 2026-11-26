# -*- coding: utf-8 -*-
"""在自己电脑上给视频配乐。

读取网易云音乐文件夹里最新的 N 首歌（支持 .ncm / mp3 / flac / m4a），
把 .ncm 转成原始音频，按歌名自动对应到 8 个年代段落，混进视频，
输出 out/GTA编年史_90秒_配乐版.mp4。

python3 src/add_music.py [--folder ~/Music/网易云音乐] [--count 8] [--replan]
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ncm2audio  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "配乐方案.json")
CONV = os.path.join(ROOT, "build", "music", "converted")
AUDIO_EXT = {".ncm", ".mp3", ".flac", ".m4a", ".aac", ".wav", ".ogg"}

ERAS = ["gta1", "gta2", "gta3", "vc", "sa", "gta4", "gta5", "gta6"]
ERA_NAME = {"gta1": "1997 GTA", "gta2": "1999 GTA 2", "gta3": "2001 GTA III", "vc": "2002 罪恶都市",
            "sa": "2004 圣安地列斯", "gta4": "2008 GTA IV", "gta5": "2013 GTA V", "gta6": "2026 GTA VI"}
# 越长越具体的关键词得分越高
KEYWORDS = {
    "gta1": ["joyride", "da shootaz", "grand theft auto 1", "gta 1", "gta1", "gta i ", "侠盗猎车手1", "侠盗猎车1", "1997"],
    "gta2": ["short change", "e-z rollers", "ez rollers", "e z rollers", "grand theft auto 2", "gta 2", "gta2", "gta ii",
             "侠盗猎车手2", "侠盗猎车2"],
    "gta3": ["grand theft auto iii", "grand theft auto 3", "gta iii", "gta 3", "gta3", "gtaiii", "craig conner",
             "侠盗猎车手3", "侠盗猎车3"],
    "vc": ["vice city", "lex horton", "gta vc", "gtavc", "罪恶都市", "罪恶城市"],
    "sa": ["san andreas", "gta sa", "gtasa", "圣安地列斯", "圣安德烈斯"],
    "gta4": ["soviet connection", "grand theft auto iv", "grand theft auto 4", "gta iv", "gta 4", "gta4", "gtaiv",
             "侠盗猎车手4", "侠盗猎车4"],
    "gta5": ["welcome to los santos", "sleepwalking", "chain gang of 1974", "grand theft auto v", "grand theft auto 5",
             "gta v", "gta 5", "gta5", "gtav", "los santos", "oh no", "侠盗猎车手5", "侠盗猎车5"],
    "gta6": ["love is a long road", "tom petty", "hot together", "pointer sisters", "grand theft auto vi",
             "grand theft auto 6", "gta vi", "gta 6", "gta6", "gtavi", "侠盗猎车手6", "侠盗猎车6"],
}


def find_songs(folder, count):
    files = []
    base_depth = folder.rstrip(os.sep).count(os.sep)
    for dirpath, dirs, fns in os.walk(folder):
        if dirpath.count(os.sep) - base_depth >= 2:
            dirs[:] = []
        for fn in fns:
            if fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() in AUDIO_EXT:
                files.append(os.path.join(dirpath, fn))
    files.sort(key=os.path.getmtime, reverse=True)
    return files[:count]


def tags(path):
    title = artist = ""
    try:
        import mutagen
        m = mutagen.File(path, easy=True)
        if m:
            title = (m.get("title") or [""])[0]
            artist = ", ".join(m.get("artist") or [])
    except Exception:
        pass
    if not title:
        stem = os.path.splitext(os.path.basename(path))[0]
        if " - " in stem:
            artist, title = stem.split(" - ", 1)
        else:
            title = stem
    return title, artist


def prepare(path):
    """Return dict(file=playable path, title, artist, src)."""
    if path.lower().endswith(".ncm"):
        os.makedirs(CONV, exist_ok=True)
        r = ncm2audio.decode(path, CONV)
        return {"file": r["out"], "title": r["title"], "artist": r["artist"], "src": path}
    t, a = tags(path)
    return {"file": path, "title": t, "artist": a, "src": path}


def match(songs):
    """One song per era: keyword matches first, the rest in download order (oldest -> 1997)."""
    scores = []
    for si, s in enumerate(songs):
        text = " ".join([s["title"], s["artist"], os.path.basename(s["src"])]).lower()
        text = " " + text.replace("_", " ") + " "
        for era in ERAS:
            best = max((len(k) for k in KEYWORDS[era] if k in text), default=0)
            if best:
                scores.append((best, si, era))
    scores.sort(reverse=True)
    plan, used = {}, set()
    for sc, si, era in scores:
        if era in plan or si in used:
            continue
        plan[era] = dict(songs[si], how="按歌名识别")
        used.add(si)
    rest = [s for i, s in enumerate(songs) if i not in used]
    rest.sort(key=lambda s: os.path.getmtime(s["src"]))
    for era in ERAS:
        if era not in plan and rest:
            plan[era] = dict(rest.pop(0), how="没认出来，按下载顺序猜的")
    for era in plan:
        plan[era].setdefault("offset", None)
        plan[era].setdefault("gain_db", 0)
    return {e: plan[e] for e in ERAS if e in plan}


def show(plan, report=None):
    off = {r["seg"]: r["offset"] for r in (report or [])}
    print()
    print("  段落              歌曲                                      从第几秒开始   怎么对上的")
    print("  " + "-" * 96)
    for era in ERAS:
        p = plan.get(era)
        if not p:
            print(f"  {ERA_NAME[era]:<14}  （没有歌，这一段不放音乐）")
            continue
        name = (p["title"] + (" - " + p["artist"] if p.get("artist") else ""))[:40]
        o = off.get(era, p.get("offset"))
        o = "自动" if o is None else f"{o:.1f}s"
        print(f"  {ERA_NAME[era]:<14}  {name:<40}  {o:<12}  {p.get('how', '')}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=os.path.expanduser("~/Music/网易云音乐"))
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--replan", action="store_true", help="忽略上次保存的配乐方案，重新识别")
    args = ap.parse_args()

    plan = None
    if os.path.exists(PLAN) and not args.replan:
        try:
            ans = input("发现上次的配乐方案（配乐方案.json）。直接用它？[Y/n] ").strip().lower()
        except EOFError:
            ans = "y"
        if ans in ("", "y", "yes", "是"):
            plan = json.load(open(PLAN, encoding="utf-8"))

    if plan is None:
        if not os.path.isdir(args.folder):
            sys.exit(f"找不到文件夹：{args.folder}\n用 --folder 指定你的音乐文件夹。")
        files = find_songs(args.folder, args.count)
        if not files:
            sys.exit(f"{args.folder} 里没有找到音乐文件（.ncm/.mp3/.flac/.m4a）。")
        print(f"在 {args.folder} 找到最新的 {len(files)} 首：")
        songs = []
        for f in files:
            try:
                s = prepare(f)
                songs.append(s)
                print("  ✓", os.path.basename(f), "→", s["title"], ("(" + s["artist"] + ")") if s["artist"] else "")
            except Exception as e:
                print("  ✗ 转换失败：", os.path.basename(f), "-", e)
        plan = match(songs)
        json.dump(plan, open(PLAN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    show(plan)
    print("正在混音……（大约半分钟）")
    import music
    final, report = music.main({k: v for k, v in plan.items()})
    show(plan, report)
    print("完成！配乐版：", final)
    print("\n想调整：打开 gta-90s/配乐方案.json，")
    print("  · 换歌对应的段落：把两段的内容互换")
    print("  · 歌从第几秒开始：把 \"offset\": null 改成秒数，比如 \"offset\": 12.5")
    print("  · 某首太响/太小：把 \"gain_db\": 0 改成 -3 或 3")
    print("改完再双击一次「一键配乐.command」，选 Y 就会按你的方案重做。")
    if sys.platform == "darwin":
        subprocess.run(["open", final])


if __name__ == "__main__":
    main()
