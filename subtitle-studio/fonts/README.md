# 字体

都是免费可商用的开源字体，体积大，不进 git。运行一次：

```bash
python fonts/download_fonts.py
```

会下载到本目录：

| 文件 | 用途 |
| --- | --- |
| `NotoSansCJKsc-Medium.otf` / `-Bold.otf` / `-Black.otf` | 思源黑体，默认 Bold |
| `fusion-pixel-12px-proportional-zh_hans.ttf` | Fusion Pixel 像素体（`pixel-red` 预设） |
| `NotoColorEmoji.ttf` | 彩色 emoji |

缺字体时会退回系统中文字体（`fc-match`），能用但字重不对。
