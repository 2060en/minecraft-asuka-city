"""Build the laptop draft: two 1x1 painting fronts become laptop screens, and
the painting back becomes the laptop's grey lid with a small Apple logo.

Run from the repository root:
    python3 addon/drafts/laptop/build.py

Resource pack only. Bedrock keeps the classic paintings in one 256x256 atlas,
textures/painting/kz.png; the seven 1x1 paintings sit in the top row at
x = 0, 16, ..., 96, and the back of every painting is the 64x64 area at
(192, 0), filled with one 16x16 wood tile repeated 4x4.

Decided 2026-11-01: two screens for now, the desktop and the code editor,
in the first two 1x1 slots; the other 1x1 paintings stay vanilla until the
author wants more screens. The lid is grey with a faint grain and a tiny
logo: a 2x2 white apple with one pixel for the leaf at its top right.

The back is shared by every painting, but backs face the wall except when a
painting stands free as a laptop lid, so the lid design goes in every 16x16
tile of the back area (how the game maps the back onto a painting needs a
test).

kz.png also holds all the bigger paintings, which become advertisements
later. Until those are drawn, this draft writes kz_overlay.png: only the
parts designed here, transparent elsewhere, to be merged into the final
atlas. The vanilla export is simply the paintings.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/laptop"

BEZEL = (22, 23, 25)
CAMERA = (52, 56, 62)
LID = (178, 182, 187)
LID_EDGE = (160, 164, 169)
LOGO = (246, 247, 248)

# ---------- screens: 16x16, display area x 1-14, y 3-12 ----------
X0, X1, Y0, Y1 = 1, 15, 3, 13


def blank():
    img = Image.new("RGBA", (16, 16), BEZEL + (255,))
    img.putpixel((7, 1), CAMERA + (255,))
    img.putpixel((8, 1), CAMERA + (255,))
    return img


def fill(px, x0, y0, x1, y1, c):
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = c + (255,)


def desktop(px):
    for y in range(Y0, Y1):
        t = (y - Y0) / (Y1 - Y0)
        c = (int(70 + 60 * t), int(110 + 40 * t), int(190 - 20 * t))
        fill(px, X0, y, X1, y + 1, c)
    fill(px, 4, 11, 12, 12, (220, 226, 236))          # dock
    for x, c in ((5, (240, 90, 80)), (7, (90, 200, 120)), (9, (250, 200, 70)), (10, (120, 160, 250))):
        px[x, 11] = c + (255,)


def code(px):
    fill(px, X0, Y0, X1, Y1, (30, 32, 40))
    lines = [(2, 9, (198, 120, 221)), (3, 12, (97, 175, 239)), (3, 8, (152, 195, 121)),
             (2, 6, (229, 192, 123)), (3, 11, (171, 178, 191)), (2, 7, (198, 120, 221))]
    for i, (x0, x1, c) in enumerate(lines):
        y = Y0 + 1 + int(i * 1.5)
        fill(px, x0, y, x1, y + 1, c)


SCREENS = {"desktop": desktop, "code": code}     # slot 0, slot 1


def screen(draw):
    img = blank()
    draw(img.load())
    return img


# ---------- lid: grey aluminium, faint grain, tiny logo ----------


def lid():
    rng = random.Random(11)
    streaks = {}
    for _ in range(7):
        y, x0 = rng.randrange(16), rng.randrange(14)
        shade = rng.choice((-3, 3))
        for x in range(x0, min(16, x0 + rng.randint(3, 5))):
            streaks[(x, y)] = shade
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            edge = x in (0, 15) or y in (0, 15)
            base = LID_EDGE if edge else LID
            d = rng.randint(-2, 2) + streaks.get((x, y), 0)
            px[x, y] = tuple(max(0, min(255, v + d)) for v in base) + (255,)
    for x, y in ((7, 7), (8, 7), (7, 8), (8, 8), (9, 6)):   # 2x2 apple, leaf at top right
        px[x, y] = LOGO + (255,)
    return img


screens = {name: screen(draw) for name, draw in SCREENS.items()}
lid_img = lid()
overlay = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
for i, img in enumerate(screens.values()):
    overlay.paste(img, (16 * i, 0))
for tx in range(4):
    for ty in range(4):
        overlay.paste(lid_img, (192 + 16 * tx, 16 * ty))
overlay.save(HERE / "kz_overlay.png")
(HERE / "meditative.png").unlink(missing_ok=True)

# Preview atlas: the screens in a row, then the lid.
n = len(screens)
atlas = Image.new("RGBA", (16 * (n + 1), 16), (0, 0, 0, 0))
for i, img in enumerate(screens.values()):
    atlas.paste(img, (16 * i, 0))
atlas.paste(lid_img, (16 * n, 0))
atlas.save(HERE / "preview_atlas.png")

# ---------- preview models: a 16x16 painting, 1 pixel thick ----------
W = 16 * (n + 1)
lid_face = {"uv": [16 * n, 0], "uv_size": [16, 16]}
edge = {"uv": [16 * n + 1, 1], "uv_size": [1, 1]}
geos = []
for i in range(n):
    geos.append({
        "description": {"identifier": f"geometry.laptop_{i}", "texture_width": W, "texture_height": 16},
        "bones": [{"name": "painting", "pivot": [0, 0, 0], "cubes": [{
            "origin": [-8, 0, -8], "size": [16, 16, 1],
            "uv": {"south": {"uv": [16 * i, 0], "uv_size": [16, 16]}, "north": lid_face,
                   "east": edge, "west": edge, "up": edge, "down": edge},
        }]}],
    })
geos.append({
    "description": {"identifier": "geometry.deck", "texture_width": W, "texture_height": 16},
    "bones": [{"name": "deck", "pivot": [0, 0, 0], "cubes": [{
        "origin": [-8, 0, -7], "size": [16, 1, 15],
        "uv": {d: edge for d in ("north", "south", "east", "west", "up", "down")},
    }]}],
})
(HERE / "preview.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos}, indent=1) + "\n",
                                       encoding="utf-8")

# ---------- preview sheet ----------
DESK = {"up": "#e3d6c2", "south": "#cbbda8", "north": "#cbbda8", "east": "#b9ab96", "west": "#b9ab96", "down": "#a59782"}
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def painting(i, x, y, z, rot=0):
    return {"type": "geo", "geo": f"{REL}/preview.geo.json", "identifier": f"geometry.laptop_{i}",
            "texture": f"{REL}/preview_atlas.png", "position": [x, y, z], "rotationY": rot}


def laptop(i, x, y, z, rot=0):
    """A painting standing free on a desk, with a thin grey deck as the keyboard."""
    return [painting(i, x, y, z, rot),
            {"type": "geo", "geo": f"{REL}/preview.geo.json", "identifier": "geometry.deck",
             "texture": f"{REL}/preview_atlas.png", "position": [x, y, z], "rotationY": rot}]


desk_row = [block(x, -16, 0, DESK) for x in range(-16, 17, 16)]
desk_row += laptop(0, -16, 0, 0) + laptop(1, 16, 0, 0)

on_wall = [block(x, 0, 0, WALL) for x in (-24, -8, 8, 24)] + [painting(0, -8, 0, 16), painting(1, 8, 0, 16)]

office = []
for x in range(-32, 33, 16):
    for z in (0, 16):
        office.append(block(x, -16, z, DESK))
office += laptop(0, -32, 0, 0) + laptop(1, 0, 0, 0) + laptop(0, 32, 0, 0)
office += laptop(1, -32, 0, 16, 180) + laptop(0, 0, 0, 16, 180) + laptop(1, 32, 0, 16, 180)

sheet = {
    "title": "筆電：桌面與寫程式兩種畫面，背面灰色加小蘋果標誌（草稿）",
    "columns": 2, "panelWidth": 560, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "兩種畫面：桌面、寫程式", "camera": {"azimuth": 0, "elevation": 0, "size": 26, "target": [0, 8, 8]},
         "objects": on_wall},
        {"label": "桌上的筆電（前面）", "camera": {"azimuth": 20, "elevation": 22, "size": 44, "target": [0, 6, 0]},
         "objects": desk_row},
        {"label": "從背面看：灰色上蓋加小蘋果標誌", "camera": {"azimuth": 200, "elevation": 15, "size": 30, "target": [-16, 8, -6]},
         "objects": desk_row},
        {"label": "辦公桌：面對面的兩排", "camera": {"azimuth": 35, "elevation": 35, "size": 80, "target": [0, 2, 8]},
         "objects": office},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote kz_overlay.png, preview files")
