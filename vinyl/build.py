"""Inline the textures into a single self-contained vinyl/index.html."""
import base64, pathlib

here = pathlib.Path(__file__).parent
html = (here / "src/template.html").read_text(encoding="utf-8")
for key, name in [("__COVER__", "cover.jpg"), ("__LABEL__", "label.jpg"), ("__SPREAD__", "spread.jpg")]:
    data = base64.b64encode((here / "src" / name).read_bytes()).decode()
    html = html.replace(key, "data:image/jpeg;base64," + data)
(here / "index.html").write_text(html, encoding="utf-8")
print("wrote", here / "index.html", len(html) // 1024, "KB")
