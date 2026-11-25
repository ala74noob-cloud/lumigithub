# -*- coding: utf-8 -*-
"""Narration script: one entry per spoken line.

tts   : text sent to the voice (numbers spelled out so they are read correctly)
card  : big on-screen text shown while the line plays (short, complete sentence)
         None  -> keep scene visuals only (era title, counters, etc.)
"""

SEGMENTS = [
    {
        "id": "hook", "year": "", "title": "", "gap_after": 0.55,
        "lines": [
            {"id": "h1", "tts": "一个靠bug活下来的游戏，",
             "card": ["一个靠BUG", "活下来的游戏"]},
            {"id": "h2", "tts": "二十九年后，新作首日卖了三十七点九亿美元。",
             "card": ["29年后，新作首日卖了", "37.9亿美元"], "big": 1},
            {"id": "h3", "tts": "九十秒，带你看完GTA一到六代。",
             "card": None},
        ],
    },
    {
        "id": "gta1", "year": "1997", "title": "GRAND THEFT AUTO", "gap_after": 0.5,
        "lines": [
            {"id": "g1a", "tts": "一九九七年，苏格兰的DMA在做一款警匪赛车游戏，",
             "card": None},
            {"id": "g1b", "tts": "可它太无聊，差点被砍掉。",
             "card": ["它无聊到", "差点被砍掉。"]},
            {"id": "g1c", "tts": "直到一个bug，让警察发了疯，追着玩家猛撞。",
             "card": ["一个BUG，", "让警察疯了。"]},
            {"id": "g1d", "tts": "测试员却玩嗨了，GTA就这么诞生了。",
             "card": ["GTA，", "就这么诞生了。"]},
        ],
    },
    {
        "id": "gta2", "year": "1999", "title": "GTA 2", "gap_after": 0.5,
        "lines": [
            {"id": "g2a", "tts": "一九九九年，刚成立的Rockstar推出GTA2，",
             "card": ["Rockstar，", "正式登场。"]},
            {"id": "g2b", "tts": "帮派开始记仇：帮一家，就得罪它的死对头。",
             "card": ["帮派，", "开始会记仇。"]},
        ],
    },
    {
        "id": "gta3", "year": "2001", "title": "GTA III", "gap_after": 0.5,
        "lines": [
            {"id": "g3a", "tts": "二零零一年，GTA3把城市搬进了3D，",
             "card": ["整座城市，", "第一次变成3D。"]},
            {"id": "g3b", "tts": "开放世界从此有了模板。",
             "card": ["开放世界，", "从此有了模板。"]},
            {"id": "g3c", "tts": "可就在发售前，九一一发生了。",
             "card": ["发售前，", "九一一发生了。"]},
            {"id": "g3d", "tts": "游戏延期，蓝白警车也改成了黑白。",
             "card": ["警车从蓝白，", "改成了黑白。"]},
        ],
    },
    {
        "id": "vc", "year": "2002", "title": "VICE CITY", "gap_after": 0.5,
        "lines": [
            {"id": "vca", "tts": "一年后的《罪恶都市》，穿越回八十年代，",
             "card": ["一年后，", "穿越回80年代。"]},
            {"id": "vcb", "tts": "主角终于开口说话，由影星雷·利奥塔配音。",
             "card": ["主角，", "终于开口说话。"]},
        ],
    },
    {
        "id": "sa", "year": "2004", "title": "SAN ANDREAS", "gap_after": 0.5,
        "lines": [
            {"id": "saa", "tts": "二零零四年，《圣安地列斯》一张地图三座城，",
             "card": ["一张地图，", "装下三座城市。"]},
            {"id": "sab", "tts": "CJ吃多了还会变胖。",
             "card": ["CJ吃多了，", "还会变胖。"]},
            {"id": "sac", "tts": "后来玩家挖出隐藏内容“热咖啡”，游戏被改成成人级下架。",
             "card": ["“热咖啡”曝光，", "游戏一度下架。"]},
            {"id": "sad", "tts": "但它依然是PS2卖得最多的游戏。",
             "card": ["它依然是", "PS2销量之王。"]},
        ],
    },
    {
        "id": "gta4", "year": "2008", "title": "GTA IV", "gap_after": 0.5,
        "lines": [
            {"id": "g4a", "tts": "二零零八年的GTA4，画面走向写实，",
             "card": ["画面，", "开始走向写实。"]},
            {"id": "g4b", "tts": "首周销售额就超过五亿美元。",
             "card": ["首周销售额，", "超过5亿美元。"]},
        ],
    },
    {
        "id": "gta5", "year": "2013", "title": "GTA V", "gap_after": 0.5,
        "lines": [
            {"id": "g5a", "tts": "二零一三年的GTA5，三个主角随时切换。",
             "card": ["三个主角，", "随时切换。"]},
            {"id": "g5b", "tts": "三天卖破十亿美元，刷新纪录；",
             "card": ["3天，", "卖破10亿美元。"]},
            {"id": "g5c", "tts": "至今卖出近两亿三千五百万份。",
             "card": ["至今卖出", "近2.35亿份。"]},
        ],
    },
    {
        "id": "gta6", "year": "2026", "title": "GTA VI", "gap_after": 0.6,
        "lines": [
            {"id": "g6a", "tts": "然后，是十三年的等待。",
             "card": ["然后，", "等了13年。"]},
            {"id": "g6b", "tts": "十七岁黑客泄露开发画面，",
             "card": ["17岁黑客，", "泄露了开发画面。"]},
            {"id": "g6c", "tts": "首支预告二十四小时播放破九千万。",
             "card": ["首支预告，", "24小时播放破9000万。"]},
            {"id": "g6d", "tts": "二零二六年十一月十九日，GTA6终于发售。",
             "card": None},
            {"id": "g6e", "tts": "首日卖出三十七点九亿美元，娱乐史上最大首发。",
             "card": ["首日37.9亿美元，", "娱乐史最大首发。"]},
        ],
    },
    {
        "id": "outro", "year": "", "title": "", "gap_after": 0.0,
        "lines": [
            {"id": "o1", "tts": "从一个bug，到史上最大首发。",
             "card": ["从一个BUG，", "到史上最大首发。"]},
            {"id": "o2", "tts": "你最爱哪一代？",
             "card": ["你最爱", "哪一代？"]},
        ],
    },
]
