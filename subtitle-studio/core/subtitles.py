"""SRT / 台词表 Markdown 导出（发给同事或老板审）。"""
from __future__ import annotations


def _ts(t: float, sep: str = ",") -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(cues: list[dict]) -> str:
    out, n = [], 0
    for c in cues:
        if c.get("kind") == "logo" or not c.get("lines"):
            continue
        n += 1
        out.append(f"{n}\n{_ts(c['start'])} --> {_ts(c['end'])}\n" + "\n".join(c["lines"]) + "\n")
    return "\n".join(out)


def to_markdown(cues: list[dict]) -> str:
    def cell(s: str) -> str:
        return s.replace("|", "\\|").replace("\n", " / ")

    rows = ["| 时间 | 原文 | 中文 |", "| --- | --- | --- |"]
    for c in cues:
        if c.get("kind") == "logo":
            continue
        zh = " / ".join(c.get("lines") or []) or ("（歌词，不翻译）" if c.get("kind") == "lyric" else "")
        rows.append(f"| {_ts(c['start'], '.')[3:]}–{_ts(c['end'], '.')[3:]} | {cell(c.get('source_text', ''))} | {cell(zh)} |")
    return "\n".join(rows) + "\n"
