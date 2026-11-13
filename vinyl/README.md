# 白胶唱片

可交互的 3D 白胶唱片页面，内含 5 首音轨。

## 目录

- `src/template.html` — 页面源码模板
- `src/cover.jpg` / `label.jpg` / `spread.jpg` — 封面、唱片标签、内页贴图
- `tracks/01–05.mp3` — 音轨
- `build.py` — 将贴图以 base64 内嵌，生成 `index.html`（独立网页）和 `artifact.html`（Artifact 版本）
- `mockups/` — 平铺效果图及合成脚本 `compose.py`

## 构建

```bash
python3 build.py
```

生成后在本目录打开 `index.html`（音轨通过相对路径 `tracks/` 加载）。
