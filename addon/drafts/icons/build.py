"""Build 3D item icons for the suitcases and the tableware (2026-11-04).

Run from the repository root, after the suitcase and tableware drafts:
    python3 addon/drafts/icons/build.py

The author asked for the suitcase icons to be drawn in 3D and the tableware
icons to be redrawn. Each piece is rendered with the preview tool
(tools/preview/) from above at an angle, like the game draws block icons,
cut out of its background and scaled into a 32 x 32 icon. The icons replace
the flat ones in addon/drafts/suitcases/icons/ and addon/drafts/tableware/icons/.
"""
import json
import subprocess
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BG = (128, 128, 128)
PANEL = 256
SIZE = 32

SUITCASES = ["cabin_navy", "large_red", "aluminium", "soft_black", "pink"]
TABLEWARE = ["plate", "bowl", "cup", "knife", "fork", "spoon", "chopsticks"]


def suitcase(name):
    return {"label": "", "camera": {"azimuth": 35, "elevation": 25, "size": 22, "target": [0, 9, 0]},
            "objects": [{"type": "geo", "geo": "/addon/drafts/suitcases/suitcases.geo.json",
                         "identifier": f"geometry.asukatech.suitcase_{name}",
                         "texture": f"/addon/drafts/suitcases/{name}.png", "position": [0, 0, 0]}]}


def tableware(name):
    size = {"plate": 13, "bowl": 10, "cup": 9, "chopsticks": 11}.get(name, 9)
    rot = 45 if name in ("knife", "fork", "spoon", "chopsticks") else 0
    return {"label": "", "camera": {"azimuth": 30, "elevation": 40, "size": size, "target": [0, 1.5, 0]},
            "objects": [{"type": "geo", "geo": "/addon/drafts/tableware/tableware.geo.json",
                         "identifier": f"geometry.asukatech.{name}", "texture": "/addon/drafts/tableware/tableware.png",
                         "position": [0, 0, 0], "rotationY": rot}]}


def cut(img):
    """Background to transparent, crop to the drawing, fit into SIZE x SIZE."""
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, _ = px[x, y]
            if abs(r - BG[0]) < 3 and abs(g - BG[1]) < 3 and abs(b - BG[2]) < 3:
                px[x, y] = (0, 0, 0, 0)
    img = img.crop(img.getbbox())
    scale = (SIZE - 2) / max(img.size)
    w, h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    small = img.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    out.alpha_composite(small, ((SIZE - w) // 2, (SIZE - h) // 2))
    return out


jobs = [(suitcase(n), ROOT / "addon/drafts/suitcases/icons" / f"{n}.png") for n in SUITCASES]
jobs += [(tableware(n), ROOT / "addon/drafts/tableware/icons" / f"{n}.png") for n in TABLEWARE]
sheet = {"columns": len(jobs), "panelWidth": PANEL, "panelHeight": PANEL,
         "background": "#%02x%02x%02x" % BG, "panels": [j[0] for j in jobs]}
sheet_path = HERE / "icons_sheet.json"
render = HERE / "icons_render.png"
sheet_path.write_text(json.dumps(sheet, indent=1) + "\n", encoding="utf-8")
subprocess.run(["node", str(ROOT / "tools/preview/render.mjs"), str(sheet_path), str(render)], check=True)
whole = Image.open(render)
row_h = whole.height                                   # one row: a panel and its (empty) label strip
for i, (_, dest) in enumerate(jobs):
    panel = whole.crop((i * PANEL, 0, (i + 1) * PANEL, PANEL))
    cut(panel).save(dest)

preview = Image.new("RGBA", (len(jobs) * 84, 84), (232, 237, 241, 255))
for i, (_, dest) in enumerate(jobs):
    preview.alpha_composite(Image.open(dest).resize((64, 64), Image.NEAREST), (i * 84 + 10, 10))
preview.save(HERE / "preview.png")
render.unlink()
print(f"wrote {len(jobs)} icons and preview.png")
