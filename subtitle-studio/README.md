# 字幕工作室（视频字幕翻译工具）

本地运行的竖屏短视频字幕翻译工具：拖入视频 → 自动识别烧录字幕 → Claude 翻译成口语化中文 → 在台词表里改 → 一键导出压制好的 MP4（音轨原样保留）。所有处理都在本机完成，只有翻译请求会发给 Anthropic API。

当前进度：**里程碑 1（最小可用版）**：烧录字幕检测 + OCR → Claude 翻译 → 台词表编辑 → 用预设硬切导出。

## 安装

需要 Python 3.10+ 和 ffmpeg（macOS：`brew install ffmpeg`；Windows：`winget install ffmpeg`）。

```bash
cd subtitle-studio
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fonts/download_fonts.py      # 思源黑体 / Fusion Pixel / Noto Color Emoji
cp .env.example .env                # 填 ANTHROPIC_API_KEY
python app.py                       # 打开 http://localhost:8000
```

OCR 默认用 RapidOCR（PaddleOCR 模型的 ONNX 版，pip 直接装好）。装了 `paddleocr` 会优先用它；也可以用环境变量 `OCR_ENGINE=paddle|rapid|easy` 指定。

## 使用

1. 点“上传视频”或直接把视频拖进窗口，上传后自动识别字幕（常驻 Logo/水印会被排除，不进台词表）。
2. 填视频简介和术语表（可选），点“自动翻译”。碎句会按意思合并，每条至少显示 1.2 秒。
3. 在台词表里改时间、中文、位置、样式。点一行，视频跳到这一段循环播放；左侧预览和最终导出用的是同一张渲染图。
4. “再给 3 个说法”和“重新翻译”只重做这一条。所有修改自动保存到 `projects/<视频名>/project.json`，可以撤销（Ctrl+Z）。
5. 点“导出视频”，在 `projects/<视频名>/exports/` 生成 `<视频名>_中文字幕_v<N>.mp4`，每次版本号 +1，不覆盖旧版。同时生成一张检查图，并对超宽、和原文重叠、时长不一致给出警告。
6. 可以下载 SRT 和“台词表 Markdown”发给同事审。

## 目录

```
app.py            FastAPI 入口 + API
core/detect.py    烧录字幕检测（抽样 OCR 找字幕带 → 掩码切时间轴 → 段内 OCR → 合并 → bbox）
core/ocr.py       OCR 引擎封装（PaddleOCR / RapidOCR / EasyOCR）
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
- 4 语音转写：faster-whisper、人声分离、歌词标记、SRT 导入
