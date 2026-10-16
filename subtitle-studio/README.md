# 字幕工作室（视频字幕翻译工具）

本地运行的竖屏短视频字幕翻译工具：拖入视频 → 自动识别烧录字幕 → Claude 翻译成口语化中文 → 在台词表里改 → 一键导出压制好的 MP4（音轨原样保留）。所有处理都在本机完成，只有翻译请求会发给 Anthropic API。

当前进度：
- **里程碑 1**：烧录字幕检测 + OCR → Claude 翻译 → 台词表编辑 → 用预设硬切导出。
- **里程碑 4（语音转写）**：视频里没有烧录字幕时，用 Whisper 听写生成台词；可选人声分离、疑似歌词提示、SRT 导入。

## 最简单的方法（Mac）

1. 下载整个代码 zip 并解压。
2. 打开“终端”，输入 `bash `（bash 后面有一个空格），把 `subtitle-studio` 文件夹里的 `启动字幕工作室.command` 拖进终端窗口，按回车。
3. 按提示操作：第一次会自动安装 Homebrew、ffmpeg、Python 和所有依赖，中途要输入一次开机密码，再粘贴一次 Claude 的 API key。装好后会自动打开浏览器。

以后每次使用都重复第 2 步，脚本会跳过已经装好的部分，直接启动。

## 手动安装

需要 Python 3.10+ 和 ffmpeg（macOS：`brew install ffmpeg`；Windows：`winget install ffmpeg`）。

```bash
cd subtitle-studio
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fonts/download_fonts.py      # 思源黑体 / Fusion Pixel / Noto Color Emoji
cp .env.example .env                # 填 ANTHROPIC_API_KEY
python app.py                       # 打开 http://localhost:8000
```

`requirements.txt` 会按电脑自动装语音转写引擎：Apple Silicon Mac（M1–M4）装 **mlx-whisper**，用 GPU 跑；其他电脑装 **faster-whisper**（有 N 卡走 CUDA）。第一次转写会自动下载模型（约 1.5GB），之后离线可用。

演出现场这类背景音乐很响的视频，可以再装 `pip install demucs`，在界面上勾选“人声分离”后再转写（会慢一些）。

OCR 默认用 RapidOCR（PaddleOCR 模型的 ONNX 版，pip 直接装好）。装了 `paddleocr` 会优先用它；也可以用环境变量 `OCR_ENGINE=paddle|rapid|easy` 指定。

## 使用

1. 点“上传视频”或直接把视频拖进窗口，上传后自动识别字幕（常驻 Logo/水印会被排除，不进台词表）。画面里没有字幕时会自动改用语音转写；也可以随时点“语音转写”手动切换。听起来像歌词的句子（副歌重复、押韵）会在备注里标“疑似歌词”，确认后把类型改成“歌词”，翻译时就会跳过。
2. 填视频简介和术语表（可选），点“自动翻译”。碎句会按意思合并，每条至少显示 1.2 秒。
3. 在台词表里改时间、中文、位置、样式。点一行，视频跳到这一段循环播放；左侧预览和最终导出用的是同一张渲染图。
4. “再给 3 个说法”和“重新翻译”只重做这一条。所有修改自动保存到 `projects/<视频名>/project.json`，可以撤销（Ctrl+Z）。
5. 点“导出视频”，在 `projects/<视频名>/exports/` 生成 `<视频名>_中文字幕_v<N>.mp4`，每次版本号 +1，不覆盖旧版。同时生成一张检查图，并对超宽、和原文重叠、时长不一致给出警告。
6. 可以下载 SRT 和“台词表 Markdown”发给同事审；也可以导入已经翻好的 SRT。

## 目录

```
app.py            FastAPI 入口 + API
core/detect.py    烧录字幕检测（抽样 OCR 找字幕带 → 掩码切时间轴 → 段内 OCR → 合并 → bbox）
core/ocr.py       OCR 引擎封装（PaddleOCR / RapidOCR / EasyOCR）
core/transcribe.py 语音转写（mlx-whisper / faster-whisper，按停顿和句末断句）
core/translate.py Claude 翻译（提示词、合并、最短时长）
core/style.py     中文字幕渲染（Pillow：底块 → 辉光 → 投影 → 描边 → emoji）
core/render.py    ffmpeg 合成导出 + 检查图
core/jobs.py      后台任务队列与进度
presets/          样式预设 JSON（gold、ice、white-shadow、white-italic-heavy、pill-light、pill-dark、tv-band、pixel-red）
web/index.html    前端（单文件）
tests/            端到端和单元测试（python -m pytest）
```

## 测试

```bash
python -m pytest
```

`tests/make_sample.py` 会生成一条带英文烧录字幕和 Logo 的 720×1280 测试视频。端到端测试替换掉 Claude 调用，检查识别文字、时间误差 ≤ 1 帧、导出带音轨、中文按时出现和消失、版本号递增。

## 后续里程碑

- 2 样式与位置：微调面板、另存预设、每个艺人的默认预设、自定义位置拖动
- 3 涂抹与淡入淡出：LaMa、半透明底块、淡入淡出曲线
