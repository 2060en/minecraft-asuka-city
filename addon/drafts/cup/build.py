"""Build the white cup draft: textures that replace the sea pickle.

Run from the repository root:
    python3 addon/drafts/cup/build.py

Resource pack only: sea_pickle.png replaces textures/blocks/sea_pickle.png and
cup_item.png replaces textures/items/sea_pickle.png, so a sea pickle is a
light steel-grey cup with water in it, 1 to 4 to a block like the vanilla pickles. The
glow under water stays (the author does not mind, 2026-11-03). The vanilla
export is simply the sea pickle. The planned glass cup (a custom block)
turns into a sea pickle in the vanilla version.

The model is built into the game. Read from the vanilla texture
(bedrock-samples, 2026-11), each pickle is a 4 x 4 column: its top face at
(4, 1), its bottom at (8, 1), the four sides 4 pixels wide side by side from
row 5 down, and the sprouts on top are two crossed planes at x 1-2 and
13-14, which become transparent. The columns are not all the same height
(in Java Edition 4 to 7 pixels), and a texture cannot change that. The
author's wish was cups of one size, by drawing the cup only within the
shortest height and leaving the rest transparent; but the side UVs start at
the top of each column, so a taller column would show its top face floating
above a shorter cup. So every side row is the same white and the cups come
out in a few heights, like different glasses. How it looks needs a test.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/cup"

# light steel grey, the colour of the steel shelf (author, 2026-11-03: not all white)
WHITE = (198, 202, 207)
WHITE_LO = (180, 184, 190)
RIM = (220, 223, 227)
WATER = (120, 176, 222)
WATER_HI = (168, 206, 236)
BOTTOM = (170, 174, 180)
OUT = (120, 124, 130)


def block_texture():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for x in range(4, 8):                      # top face: a rim round the water
        for y in range(1, 5):
            px[x, y] = RIM + (255,)
    for x, y in ((5, 2), (6, 2), (5, 3), (6, 3)):
        px[x, y] = WATER + (255,)
    px[5, 2] = WATER_HI + (255,)
    for x in range(8, 12):                     # bottom face
        for y in range(1, 5):
            px[x, y] = BOTTOM + (255,)
    for y in range(5, 16):                     # sides: one white, a lighter rim row, shade on one edge
        for x in range(16):
            c = RIM if y == 5 else (WHITE_LO if x % 4 == 3 else WHITE)
            px[x, y] = c + (255,)
    return img


def item_texture():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(4, 14):
        for x in range(4, 12):
            px[x, y] = (WHITE_LO if x >= 10 else WHITE) + (255,)
    for x in range(5, 11):                     # the water seen over the rim
        px[x, 4] = WATER + (255,)
    px[6, 4] = WATER_HI + (255,)
    for y in range(3, 15):                     # outline
        for x in range(3, 13):
            if px[x, y][3] == 0 and any(px[x + dx, y + dy][3] and px[x + dx, y + dy][:3] != OUT
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < 16 and 0 <= y + dy < 16):
                px[x, y] = OUT + (255,)
    return img


block_texture().save(HERE / "sea_pickle.png")
item_texture().save(HERE / "cup_item.png")

# Preview model: Java Edition's sea pickle columns (4 x h x 4), UVs as read above.
COLUMNS = {   # count: [(x, z, height)], in 1/16 of a block
    1: [(6, 6, 6)],
    2: [(3, 3, 6), (8, 8, 4)],
    3: [(6, 9, 6), (2, 2, 4), (8, 1, 6)],
    4: [(2, 2, 7), (9, 10, 4), (9, 2, 6), (1, 9, 5)],
}


def column(x, z, h):
    def f(u):
        return {"uv": [u, 5], "uv_size": [4, h]}
    return {"origin": [x - 8, 0, z - 8], "size": [4, h, 4],
            "uv": {"north": f(0), "east": f(4), "south": f(8), "west": f(12),
                   "up": {"uv": [4, 1], "uv_size": [4, 4]}, "down": {"uv": [8, 1], "uv_size": [4, 4]}}}


geos = [{"description": {"identifier": f"geometry.cups_{n}", "texture_width": 16, "texture_height": 16},
         "bones": [{"name": "cups", "pivot": [0, 0, 0], "cubes": [column(*c) for c in cols]}]}
        for n, cols in COLUMNS.items()]
(HERE / "cup_preview.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos},
                                                      indent=1) + "\n", encoding="utf-8")

TABLE = {"up": "#e9e4da", "south": "#d6d0c4", "north": "#d6d0c4", "east": "#c4beb2", "west": "#c4beb2", "down": "#b0aa9e"}
objs = []
for i, n in enumerate(COLUMNS):
    x = (i - 1.5) * 16
    objs.append({"type": "block", "color": TABLE, "origin": [x - 8, -16, -8], "size": [16, 16, 16]})
    objs.append({"type": "geo", "geo": f"{REL}/cup_preview.geo.json", "identifier": f"geometry.cups_{n}",
                 "texture": f"{REL}/sea_pickle.png", "position": [x, 0, 0]})
sheet = {"title": "淺灰色鐵杯：海鞘換材質（草稿，1～4 個，高度照 Java 版推測）",
         "columns": 2, "panelWidth": 560, "panelHeight": 300, "background": "#e8edf1",
         "panels": [
             {"label": "斜看", "camera": {"azimuth": 30, "elevation": 30, "size": 40, "target": [0, 2, 0]}, "objects": objs},
             {"label": "正面", "camera": {"azimuth": 0, "elevation": 8, "size": 40, "target": [0, 2, 0]}, "objects": objs},
         ]}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote sea_pickle.png, cup_item.png, cup_preview.geo.json, preview.json")
