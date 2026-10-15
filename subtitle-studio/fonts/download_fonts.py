"""下载字体到 fonts/。"""
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CJK = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-{w}.otf"
EMOJI = "https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf"
PIXEL_API = "https://api.github.com/repos/TakWolf/fusion-pixel-font/releases/latest"


def fetch(url: str) -> bytes:
    print("下载", url)
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def main():
    try:
        download_all()
    except OSError as e:
        sys.exit(f"下载失败：{e}\n可以手动下载后放进 {HERE}（见 README.md）")


def download_all():
    for w in ("Medium", "Bold", "Black"):
        p = HERE / f"NotoSansCJKsc-{w}.otf"
        if not p.exists():
            p.write_bytes(fetch(CJK.format(w=w)))
    p = HERE / "NotoColorEmoji.ttf"
    if not p.exists():
        p.write_bytes(fetch(EMOJI))
    if not list(HERE.glob("fusion-pixel-12px-proportional-zh_hans.*")):
        try:
            assets = json.loads(fetch(PIXEL_API))["assets"]
            url = next(a["browser_download_url"] for a in assets
                       if "12px-proportional" in a["name"] and "ttf" in a["name"] and a["name"].endswith(".zip"))
            with zipfile.ZipFile(io.BytesIO(fetch(url))) as z:
                for n in z.namelist():
                    if "zh_hans" in n and n.endswith((".ttf", ".otf")):
                        (HERE / Path(n).name).write_bytes(z.read(n))
        except Exception as e:  # noqa: BLE001
            print("像素体下载失败，可以手动从 https://github.com/TakWolf/fusion-pixel-font/releases 下载：", e, file=sys.stderr)
    print("完成")


if __name__ == "__main__":
    main()
