from core import style, translate
from core.project import new_cue


def _cue(i, s, e, text, kind="caption", bbox=(100, 400, 600, 440)):
    return new_cue(id=f"c{i:02d}", start=s, end=e, source_text=text, source_bbox=list(bbox), kind=kind)


def test_parse_json_array_tolerates_fences():
    assert translate.parse_json_array('好的\n```json\n[{"merge_ids":["c01"],"lines":["嗨"]}]\n```') == \
        [{"merge_ids": ["c01"], "lines": ["嗨"]}]


def test_apply_merges_and_keeps_unreferenced():
    cues = [_cue(1, 0.3, 0.8, "I felt a lot more safe"), _cue(2, 0.8, 1.6, "with you", bbox=(150, 450, 500, 490)),
            _cue(3, 2.0, 4.0, '"run away with me"', kind="lyric"), _cue(4, 5.0, 7.0, "bye")]
    result = [
        {"merge_ids": ["c01", "c02"], "lines": ["有你在", "安全感直接拉满"], "note": "调换语序"},
        {"merge_ids": ["c03"], "lines": [], "skip": True},
        {"merge_ids": ["c99"], "lines": ["不存在的 id 要忽略"]},
    ]
    out = translate.apply(cues, result)
    assert [c["source_ids"] if "source_ids" in c else c["id"] for c in out] == [["c01", "c02"], ["c03"], "c04"]
    merged = out[0]
    assert (merged["start"], merged["end"]) == (0.3, 1.6)
    assert merged["source_bbox"] == [100, 400, 600, 490]
    assert merged["lines"] == ["有你在", "安全感直接拉满"] and merged["note"] == "调换语序"
    assert out[1]["kind"] == "lyric" and out[1]["lines"] == []
    assert out[2]["lines"] == []   # 没被引用的原样保留


def test_min_duration_extends_but_not_past_next():
    cues = [_cue(1, 0.0, 0.5, "a"), _cue(2, 0.9, 3.0, "b"), _cue(3, 5.0, 5.4, "c")]
    out = translate.enforce_min_duration(cues)
    assert out[0]["end"] == 0.9      # 只能延长到下一条开始
    assert out[2]["end"] == 6.2      # 1.2 秒


def test_layout_respects_safe_width_and_bottom_alignment():
    presets = style.load_presets()
    long = new_cue(lines=["这一行特别特别特别特别特别特别特别长的中文字幕"], source_bbox=[100, 400, 600, 440])
    r = style.render(long, presets, 720, 1280)
    assert r["image"].width <= 720 * style.SAFE_WIDTH_RATIO + 10
    assert "文字超出安全宽度，已自动缩小字号" in r["warnings"]

    one = style.render(new_cue(lines=["一行"], placement="above", source_bbox=[100, 600, 600, 640]), presets, 720, 1280)
    two = style.render(new_cue(lines=["第一行", "第二行"], placement="above", source_bbox=[100, 600, 600, 640]), presets, 720, 1280)
    assert abs((one["y"] + one["image"].height) - (two["y"] + two["image"].height)) <= 3   # 底边不动
    assert one["y"] + one["image"].height < 600


def test_emoji_is_rendered_in_color():
    r = style.render(new_cue(lines=["好耶😂"], source_bbox=[100, 400, 600, 440]), style.load_presets(), 720, 1280)
    px = r["image"].convert("RGB").getdata()
    # 金色字 + 黄色 emoji 之外应该出现 emoji 的蓝色泪滴
    assert any(b > 150 and b > r_ + 40 for r_, g, b in px)
