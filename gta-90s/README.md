# 90秒看完GTA 1-6代（2D 动画短片）

成片在 `out/` 目录：

| 文件 | 说明 |
|---|---|
| `out/GTA编年史_90秒.mp4` | 成片：1920×1080，30fps，含解说和音效（不含音乐），响度 -15 LUFS，内嵌章节 |
| `out/GTA编年史_90秒_音乐打点.txt` | 每代音乐的入点和出点、关键节拍、混音建议 |
| `out/GTA编年史_90秒_markers.csv` | 同一套打点的表格版 |
| `out/GTA编年史_90秒_字幕.srt` | 完整解说字幕（画面上只放精简大字，这份可选用） |
| `out/GTA编年史_90秒_考证资料.md` | 每句解说的出处 |
| `out/stems/voice.flac`、`sfx.flac` | 人声、音效分轨（和成片时间轴对齐），方便你加音乐后重新混 |

## 重新生成

```bash
pip install edge-tts numpy scipy soundfile fonttools
python3 src/tts.py --rate +14%   # 解说配音（微软 zh-CN-YunxiNeural），需要能访问 speech.platform.bing.com
python3 src/timeline.py          # 排时间轴、导出逐字节拍
python3 src/sfx.py               # 程序化音效 + 人声混音
node src/render.js 4 30          # Playwright + Canvas 逐帧渲染
python3 src/package.py           # 合成成片、分轨、打点表、字幕
```

- 改解说词：`src/script.py`
- 画面：`src/scenes.js`（每代一个场景）、`src/main.js`（开场、转场、大字卡、通缉星级 HUD）
- 单帧预览：`node src/still.js build/stills 12.5 40`

字体：站酷庆科黄油体、Noto Sans SC（OFL，来自 @fontsource）、得意黑 Smiley Sans（OFL）、Anton、Bebas Neue、Bowlby One（OFL）。
