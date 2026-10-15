"""Claude 翻译（指南第 4 部分）。

一次把整条视频的台词连同上下文发过去，返回 JSON；碎句按完整意思合并。
API key 只从环境变量 / .env 读取。
"""
from __future__ import annotations

import json
import os
import re

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
MIN_DURATION = 1.2

SYSTEM = """你是一位电子音乐艺人的中文社媒运营。把下面的短视频字幕翻译成自然、口语、带点幽默的简体中文，像中文博主自己写的，而不是直译。
- 输入：按时间顺序的台词列表（id, start, end, text, kind）、视频简介、术语表。
- 输出：只返回 JSON 数组，每项 {"merge_ids": [...], "lines": [...], "note": "", "skip": false}，不要输出任何其他文字。
- 碎句（逐词或半句）按完整中文意思合并，merge_ids 按时间顺序列出被合并的原台词 id；每个 id 恰好出现一次。
- 每行 ≤ 16 个中文字，最多 2 行（长段叙述文案除外）；断行处的逗号可以省掉。
- 为了中文通顺可以调换相邻两句的顺序，此时把两句一起放进 merge_ids。
- 口语化、本地化，可以用国内年轻人熟悉的说法，但不堆碎梗、不土。
- 保留原文笑点；双关无法直译时做中文等效梗，并在 note 里说明改动。
- 保留原文的 emoji，放在中文句末。
- 艺人名、厂牌名、活动名、@账号、ID、drop、house、rave 保留英文；歌名用书名号；地名用通用中文译名；其余专有名词按术语表。
- 避开政治、宗教等敏感表述；酒类广告不写导购和劝饮。
- kind=lyric 的条目不翻译，原样返回 {"merge_ids": [id], "lines": [], "skip": true}。
- kind=title 是章节标题，kind=label 是画面标注（如 Me / Bodyguard），各自单独翻译、不和其他条目合并。"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _ask(user: str, client: anthropic.Anthropic | None = None, max_tokens: int = 32000) -> str:
    client = client or _client()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude 拒绝了这次翻译请求，请检查台词内容后重试。")
    return "".join(b.text for b in msg.content if b.type == "text")


def parse_json_array(text: str) -> list:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError(f"翻译结果不是 JSON 数组：{text[:200]}")
    return json.loads(text[start:end + 1])


def build_request(cues: list[dict], description: str = "", glossary: dict | None = None) -> str:
    items = [{"id": c["id"], "start": c["start"], "end": c["end"], "text": c["source_text"], "kind": c.get("kind", "caption")}
             for c in cues if c.get("kind") != "logo"]
    return json.dumps({
        "video_description": description,
        "glossary": glossary or {},
        "cues": items,
    }, ensure_ascii=False, indent=1)


def apply(cues: list[dict], result: list[dict]) -> list[dict]:
    """按 merge_ids 合并原台词，返回新的 cue 列表（未被引用的原台词原样保留）。"""
    by_id = {c["id"]: c for c in cues}
    used: set[str] = set()
    out: list[dict] = []
    for item in result:
        ids = [i for i in item.get("merge_ids", []) if i in by_id and i not in used]
        if not ids:
            continue
        used.update(ids)
        group = sorted((by_id[i] for i in ids), key=lambda c: c["start"])
        base = json.loads(json.dumps(group[0]))
        boxes = [c["source_bbox"] for c in group if c.get("source_bbox")]
        base.update({
            "start": min(c["start"] for c in group),
            "end": max(c["end"] for c in group),
            "source_text": "\n".join(c["source_text"] for c in group),
            "source_ids": ids,
            "lines": [] if item.get("skip") else [str(x).strip() for x in item.get("lines", []) if str(x).strip()],
            "note": str(item.get("note") or ""),
        })
        if boxes:
            base["source_bbox"] = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                                   max(b[2] for b in boxes), max(b[3] for b in boxes)]
        if item.get("skip"):
            base["kind"] = "lyric"
        out.append(base)
    out += [json.loads(json.dumps(c)) for c in cues if c["id"] not in used]
    out.sort(key=lambda c: c["start"])
    return enforce_min_duration(out)


def enforce_min_duration(cues: list[dict], min_dur: float = MIN_DURATION) -> list[dict]:
    """每条中文至少显示 1.2 秒；不够就往后延长，但不压到下一条开始之后。"""
    for i, c in enumerate(cues):
        if c["end"] - c["start"] >= min_dur:
            continue
        nxt = min((d["start"] for d in cues[i + 1:] if d["start"] > c["start"]), default=None)
        target = c["start"] + min_dur
        c["end"] = round(min(target, nxt) if nxt is not None else target, 3)
    return cues


def translate(cues: list[dict], description: str = "", glossary: dict | None = None,
              client: anthropic.Anthropic | None = None) -> list[dict]:
    if not cues:
        return []
    raw = _ask(build_request(cues, description, glossary), client)
    return apply(cues, parse_json_array(raw))


def alternatives(cue: dict, context: list[dict], n: int = 3, description: str = "", glossary: dict | None = None,
                 client: anthropic.Anthropic | None = None) -> list[list[str]]:
    """“重新翻译这一条”（n=1）/“再给 3 个备选说法”（n=3）。返回 n 组 lines。"""
    req = build_request(context, description, glossary)
    user = (f"{req}\n\n只翻译 id={cue['id']} 这一条（原文：{cue['source_text']!r}），"
            f"给出 {n} 个风格不同的说法。只返回 JSON 数组，每项 {{\"lines\": [...]}}。")
    items = parse_json_array(_ask(user, client, max_tokens=4000))
    return [[str(x) for x in it.get("lines", [])] for it in items if isinstance(it, dict)][:n]
