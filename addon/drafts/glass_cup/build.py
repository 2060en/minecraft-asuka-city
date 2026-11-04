"""Build the glass cup draft: a custom block, 1 to 4 glasses of water.

Run from the repository root:
    python3 addon/drafts/glass_cup/build.py
    node tools/preview/render.mjs addon/drafts/glass_cup/preview.json addon/drafts/glass_cup/preview.png

Like the takeaway coffee cup (addon/drafts/coffee_cup/): use a glass on a
glass to add one, up to four, on the same spots as the coffee cups. The
glass is see-through, with water inside (the block's render method is
"blend"). In the vanilla version it becomes a sea pickle with the same
count, which the resource pack shows as a steel cup (addon/drafts/cup/);
decided by the author 2026-11-03.

Each glass is 3 x 4 x 3 pixels (about 14 x 19 cm; the world's small props
are drawn about twice real size, like the coffee cup), an octagonal prism
(author, 2026-11-04): a base, eight thin walls, open at the top, with water
inside to just over half.
"""
import json
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/glass_cup"

GLASS = (214, 232, 242, 96)
GLASS_EDGE = (236, 246, 252, 170)
WATER = (104, 168, 220, 210)         # nearly opaque, so the overlapping bars inside do not show
WATER_TOP = (150, 198, 236, 190)
BASE = (220, 236, 246, 200)

# 16 x 16 texture of swatches, 4 x 4 each
SWATCH = {"glass": (0, 0), "edge": (4, 0), "water": (8, 0), "water_top": (12, 0), "base": (0, 4)}
COLOURS = {"glass": GLASS, "edge": GLASS_EDGE, "water": WATER, "water_top": WATER_TOP, "base": BASE}


def texture():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for name, (u, v) in SWATCH.items():
        for y in range(v, v + 4):
            for x in range(u, u + 4):
                px[x, y] = COLOURS[name]
    for x in range(4, 8):          # the rim: a brighter top row on the edge swatch
        px[x, 0] = (250, 252, 255, 210)
    return img


def sw(name, w=4, h=4):
    u, v = SWATCH[name]
    return {"uv": [u, v], "uv_size": [w, h]}


R = 1.5                                       # half the width across the flats
SIDE = 2 * R * math.tan(math.radians(22.5))   # one side of the octagon


def octagon(cx, cz, y, h, r, faces, lift=0.0):
    """A solid octagonal prism: four bars, each 2r long and one side wide,
    turned 0, 45, 90 and 135 degrees about the centre, fill an octagon
    exactly. Each bar's top sits `lift` higher than the last so the
    overlapping tops do not flicker."""
    side = 2 * r * math.tan(math.radians(22.5))
    return [{"origin": [cx - r, y, cz - side / 2], "size": [2 * r, h + i * lift, side], "uv": faces,
             "pivot": [cx, y, cz], "rotation": [0, i * 45, 0]} for i in range(4)]


def glass(cx, cz):
    """One octagonal glass centred on (cx, cz) (author, 2026-11-04): a base,
    eight thin walls, each one side of the octagon turned in 45-degree steps,
    open at the top with a bright rim, and the water to just over half."""
    T = 0.35                                   # wall thickness
    wall_faces = {f: sw("glass") for f in ("north", "south", "east", "west")}
    wall_faces["up"] = sw("edge")              # the rim
    walls = [{"origin": [cx - SIDE / 2, 0.5, cz + R - T], "size": [SIDE, 3.5, T], "uv": wall_faces,
              "pivot": [cx, 0, cz], "rotation": [0, k * 45, 0]} for k in range(8)]
    water = {f: sw("water") for f in ("north", "south", "east", "west", "down")}
    water["up"] = sw("water_top")
    base = {f: sw("base") for f in ("north", "south", "east", "west", "up", "down")}
    return octagon(cx, cz, 0, 0.5, R, base) + walls + octagon(cx, cz, 0.5, 2.2, R - T, water, lift=0.01)


# the same spots as the coffee cups (addon/drafts/coffee_cup/coffee_cup.geo.json)
SPOTS = {1: [(0, 0)], 2: [(-3, -1), (3, 1)], 3: [(-3, -2), (3, -2), (0, 3)], 4: [(-3, -3), (3, -3), (-3, 3), (3, 3)]}
bones = [{"name": f"count_{n}", "pivot": [0, 0, 0], "cubes": [c for s in spots for c in glass(*s)]}
         for n, spots in SPOTS.items()]
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.glass_cup", "texture_width": 16, "texture_height": 16},
    "bones": bones}]}
texture().save(HERE / "glass_cup.png")
(HERE / "glass_cup.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
TABLE = {"up": "#c9a27a", "south": "#b38d66", "north": "#b38d66", "east": "#a17d58", "west": "#a17d58", "down": "#8e6c4a"}
objs = []
for i, n in enumerate(SPOTS):
    x = (i - 1.5) * 16
    objs.append({"type": "block", "color": TABLE, "origin": [x - 8, -16, -8], "size": [16, 16, 16]})
    objs.append({"type": "geo", "geo": f"{REL}/glass_cup.geo.json", "bones": [f"count_{n}"],
                 "texture": f"{REL}/glass_cup.png", "position": [x, 0, 0]})
sheet = {"title": "八角形玻璃水杯（自製方塊，草稿）：1～4 杯，原味版是海鞘",
         "columns": 2, "panelWidth": 560, "panelHeight": 300, "background": "#e8edf1",
         "panels": [
             {"label": "斜看", "camera": {"azimuth": 30, "elevation": 30, "size": 40, "target": [0, 2, 0]}, "objects": objs},
             {"label": "近看", "camera": {"azimuth": 25, "elevation": 28, "size": 18, "target": [24, 2, 0]}, "objects": objs},
         ]}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote glass_cup.png, glass_cup.geo.json, preview.json")
