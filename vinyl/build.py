"""Inline the textures into a single self-contained vinyl/index.html."""
import base64, pathlib

here = pathlib.Path(__file__).parent
html = (here / "src/template.html").read_text(encoding="utf-8")
for key, name in [("__COVER__", "cover.jpg"), ("__LABEL__", "label.jpg"), ("__SPREAD__", "spread.jpg")]:
    data = base64.b64encode((here / "src" / name).read_bytes()).decode()
    html = html.replace(key, "data:image/jpeg;base64," + data)
(here / "index.html").write_text(html, encoding="utf-8")
print("wrote", here / "index.html", len(html) // 1024, "KB")

# Artifact variant: the host adds its own doctype/html/head/body skeleton.
import re
frag = re.sub(r"<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", html, flags=re.I)
frag = frag.replace("</head>\n<body>\n", "").replace("</body>\n</html>\n", "")
frag = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", frag)
(here / "artifact.html").write_text(frag, encoding="utf-8")
print("wrote", here / "artifact.html")
