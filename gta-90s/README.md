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
| `一键配乐.command` | 在 Mac 上双击，把网易云音乐里最新的 8 首歌配进视频（见下文） |

## 在自己的 Mac 上配乐（一键）

不用上传歌。脚本会直接读取你电脑上 `~/Music/网易云音乐` 里**最新的 8 首**（支持 `.ncm`），转换后按年代放进视频。

1. 下载本分支的 ZIP 包并解压：
   https://github.com/ala74noob-cloud/lumigithub/archive/refs/heads/claude/exciting-pasteur-998f9s.zip
2. 打开解压后的 `gta-90s` 文件夹，**右键「一键配乐.command」→ 打开 → 打开**。第一次必须用右键，否则 macOS 会拦截；以后双击即可。
3. 第一次运行会自动装好需要的组件，大约 1~3 分钟，**不需要单独装 ffmpeg**。完成后会自动打开 `out/GTA编年史_90秒_配乐版.mp4`。

- 终端里会列出每首歌放在哪一段、从第几秒开始。认不出歌名的，会按下载顺序猜，并标上“猜的”。
- 想调整就改 `配乐方案.json`：换段落、改起始秒数 `offset`、改音量 `gain_db`。改完再运行一次，选 Y。
- 文件夹不在默认位置：在终端里运行 `bash 一键配乐.command --folder "/你的/音乐文件夹"`。
- 如果提示需要 Python：在终端里运行 `xcode-select --install`，装好后再运行。

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
