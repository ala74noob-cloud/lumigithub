# gta-90s：90秒看完 GTA 1-6 代（2D 动画短片）

整条流水线都是代码：中文解说经 TTS 合成，按逐字时间排进时间轴；Canvas 逐帧画原创 2D 插画；numpy 程序化合成音效；ffmpeg 合成成片。
画面不用任何游戏截图、Logo 或角色形象。

成片规格：1920×1080，30fps，90.44 秒，响度 -16 LUFS / -1.5 dBTP，H.264 + AAC。

## 流水线（按顺序运行，每一步读上一步的产物）

```
src/script.py      解说词 + 屏幕大字（唯一需要手改的“剧本”）
   │
src/tts.py         edge-tts（zh-CN-YunxiNeural, +14%）逐句合成 → build/tts/<id>.wav + durations.json（含逐字时间）
   │
src/timeline.py    把句子排上时间轴 → build/timeline.json、data/timeline.json、src/timeline.js（window.TL）
   │               含 segments（10 段起止）、lines（每句起止 + 逐字时间）、beats（关键词时刻，画面和音效都靠它对齐）
   ├────────────────────────────┐
src/sfx.py                      src/render.js（Playwright 打开 src/index.html，4 个页面并行逐帧截图 → ffmpeg）
 程序化音效 + 人声处理 + 闪避      → build/video/video.mp4
 → build/audio/{voice,sfx,mix}.wav
   └────────────┬───────────────┘
src/package.py     响度标准化、编码成片、字幕 SRT、音乐打点表、分轨 → out/

（可选）src/add_music.py ← 一键配乐.command
           读网易云文件夹最新 N 首 → src/ncm2audio.py 解 .ncm → 按歌名对应年代 → src/music.py 混音
           → out/GTA编年史_90秒_配乐版.mp4（不提交，仓库是公开的，歌有版权）
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `src/script.py` | `SEGMENTS`：10 段（hook、gta1、gta2、gta3、vc、sa、gta4、gta5、gta6、outro），每段若干 `lines`。`tts` 是念的字（数字要写成汉字，比如“一九九七年”），`card` 是屏幕上的两行大字 `[小行, 大行]`，`None` 表示这句不出大字 |
| `src/tts.py` | 只重做改过的句子（用文本 + 声音 + 语速做缓存 key），`--force` 全部重做。会切掉首尾静音，逐字时间同步平移 |
| `src/timeline.py` | 间隔常量：`LEAD` / `GAP` / `SEG_GAP` / `TAIL` / `PRE`（个别句子前的戏剧停顿）。`beats` 字典用 `word_time(句子id, 关键词)` 取某个词开始的时刻，**加新画面或音效节拍就在这里加** |
| `src/index.html` | 只负责加载字体和 4 个 JS，画布 1920×1080 |
| `src/engine.js` | 工具和画笔：缓动 `E`、种子随机 `rng` / `hash`、`skyline` 天际线、`palm` 棕榈、`carSide` 侧面车、`person` 人物剪影（参数：fat、female、pose、rim、shirt、hood）、`halftone` 网点、`outlinedText`（GTA 式粗黑描边 + 投影，数字可单独上色）、`stamp` 印章、`GRAIN` 颗粒 |
| `src/scenes.js` | `SCENES[段id] = { init(), draw(ctx, t, opt) }`，每代一个场景，`t` 是**全局秒数**。<br>gta1：像素俯视追车，含警察 bug。gta2：霓虹俯视 + 帮派好感面板。gta3：Mode-7 从 2D 倾斜成 3D → 雨夜城市 → 9·11 日历 → 警车重新涂装。vc：录像带倒带到 1986 → 霓虹日落。sa：三城分屏 → CJ 变胖 → 热咖啡 / AO 印章 → 王冠。gta4：灰调天台。gta5：三主角切换 + 金额计数器。gta6：等待 / 泄露 / 预告 → 揭晓 → 37.9 亿。<br>文件末尾的 `MONTAGE` 是开场快闪用的 8 个代表帧时刻 |
| `src/main.js` | 总调度 `render(t)`，绘制顺序：场景（含 0.26 秒斜切转场）→ 年代大标题 / 左上角徽章 → 右上通缉星 → 底部年代轴 → 大字卡 → 颗粒 → 暗角 → 首尾淡入淡出。<br>`ERA` 是各代配色和星数；`drawHook` 负责快闪和“90秒”标题；`CARDS` 根据 `script.py` 自动排大字的出现和消失时间 |
| `src/render.js` | `node src/render.js [并行数] [fps]`，分块并行渲染后无损拼接 |
| `src/still.js` | `node src/still.js 输出目录 12.5 40 ...`：只渲染指定秒数的单帧 JPG。**改画面时先用它看，别每次全片渲染** |
| `src/sfx.py` | 上半部分是 40 多种音效配方（impact、whoosh、radio_tune 换台声、cash_register、siren8、vhs_rewind、firework……）。<br>下半部分用 `put(声音, 时刻, 增益dB, bed=是否环境音)` 按 `beats` 摆放。<br>人声处理：高通 → 压缩 → 提亮。说话时音效自动压低约 7 dB，环境音压低约 11 dB |
| `src/package.py` | 两遍 loudnorm（先 alimiter 削峰，保证走 linear 模式）、编码 CRF 21、生成 SRT / 打点表 / markers.csv、导出分轨 FLAC |
| `src/music.py` | 每代一首歌：自动跳过安静前奏并对齐重拍，按 BS.1770 统一到 -23 LUFS，说话时再压 9 dB，最后整体 -16 LUFS，视频流直接复制 |
| `src/ncm2audio.py` | 网易云 `.ncm` 解密：AES 核心密钥 + RC4 式密钥盒，兼容新旧两种封面块布局；`--selftest` 自检 |
| `src/add_music.py` | 选最新 N 首、按关键词把歌对应到年代（`KEYWORDS`）、生成可手改的 `配乐方案.json` |
| `data/timeline.json` | `timeline.py` 产物的副本（会提交进 git），新克隆的仓库可以直接渲染或配乐 |
| `assets/fonts/` | 站酷庆科黄油体（主标题）、得意黑（小行字）、Anton（数字）、Bebas Neue / Bowlby One（英文）、Noto Sans SC 900（备用），全部 OFL 授权 |
| `out/` | 交付物：成片、打点表、字幕、考证资料、`stems/voice.flac` 和 `sfx.flac` |

## 铁律

1. **每一帧必须只依赖 `t`。** 不能在帧与帧之间保存状态，粒子、车辆位置都用 `t` 和 `hash(i)` 算出来。4 个渲染进程各画一段，带状态就会出错。
2. **时间对齐只用 `beats` 和 `LINES[id].start / end`**，不要在画面或音效里手写秒数。改了解说词，重新跑 `tts.py → timeline.py`，画面和音效会自动跟着走。
3. **大字卡只写短的完整句。** 两行：小行用得意黑，大行用黄油体，数字自动用强调色。注意黄油体里“它”像“已”，容易看错的字要换字或改写。
4. **新加的屏幕文字要加进 `main.js` 的 `init()` 里 `texts` 列表。** 中文字体是按字分包的子集，不预加载会退回系统字体。
5. **仓库是公开的。** 不要提交带版权音乐的配乐版、`配乐方案.json` 或 `.ncm` 文件，`.gitignore` 已经拦了。
6. **事实性文案改动要同步更新 `out/GTA编年史_90秒_考证资料.md`。**

## 常见修改

| 想做的事 | 怎么做 |
|---|---|
| 改解说或大字 | 改 `script.py` → `tts.py` → `timeline.py` → `sfx.py` → `render.js` → `package.py`。如果用到的 `beats` 关键词变了，`timeline.py` 会报 KeyError，去改对应的 `word_time` |
| 只改画面 | 改 `scenes.js` / `main.js` → 用 `still.js` 看单帧 → `render.js` → `package.py` |
| 只改音效 | 改 `sfx.py` → `package.py`（不用重新渲染画面） |
| 换声音或语速 | `python3 src/tts.py --voice zh-CN-YunjianNeural --rate +10% --force`，然后重跑后续所有步骤（总时长会变） |
| 加一个新音效 | 在 `sfx.py` 写一个返回 `(N, 2)` 数组的函数，然后用 `put(新函数(), B["某拍"], -12)` 放到对应时刻 |
| 做竖屏 9:16 | 改 `engine.js` 的 `W` / `H`、`index.html` 的画布尺寸、`render.js` 的 viewport，再把各场景里写死的坐标改成按 `W` / `H` 计算（这是最大的工作量） |

## 本地环境（macOS）

```bash
brew install ffmpeg node python          # tts.py / render.js / package.py 需要系统 ffmpeg；配乐那一步不需要
cd gta-90s
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install && npx playwright install chromium
```

- `tts.py` 需要能访问 `speech.platform.bing.com`。
- 中间产物都在 `build/`，不进 git。新克隆的仓库要从 `tts.py` 开始跑；如果只想重新配乐，直接用 `一键配乐.command`（用的是 `data/` 和 `out/stems`）。

## 检查方法

```bash
node src/still.js build/stills 9.5 33 81                                  # 看单帧
ffmpeg -pattern_type glob -i 'build/stills/t*.jpg' -vf "scale=640:360,tile=3x3" -frames:v 1 build/sheet.jpg   # 拼成联系表
ffmpeg -i out/GTA编年史_90秒.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12                # 测响度
python3 -I src/ncm2audio.py --selftest
```
