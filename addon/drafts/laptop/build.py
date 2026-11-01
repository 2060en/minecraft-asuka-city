"""Build the laptop draft: 1x1 painting fronts become laptop screens, and the
painting back becomes the laptop's grey lid with an Apple logo.

Run from the repository root:
    python3 addon/drafts/laptop/build.py

Resource pack only. Bedrock keeps the classic paintings in one 256x256 atlas,
textures/painting/kz.png; the seven 1x1 paintings sit in the top row at
x = 0, 16, ..., 96, and the back of every painting is the 64x64 area at
(192, 0), filled with one 16x16 wood tile repeated 4x4. Newer paintings
have their own files; meditative.png is the only new 1x1 one.

Painting placement picks a random design among those that fit, so all eight
1x1 designs are laptop screens with different pictures: whichever comes up,
it is a laptop. The back is shared by every painting, but backs face the wall
except when a painting stands free as a laptop lid, so the lid design goes in
every 16x16 tile of the back area (how the game maps the back onto a
painting needs a test).

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
LOGO = (234, 236, 238)

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
    for x, c in ((5, (240, 90, 80)), (7, (90, 200, 120)), (9, (250, 200, 70)), (11 - 1, (120, 160, 250))):
        px[x, 11] = c + (255,)


def code(px):
    fill(px, X0, Y0, X1, Y1, (30, 32, 40))
    lines = [(2, 9, (198, 120, 221)), (3, 12, (97, 175, 239)), (3, 8, (152, 195, 121)),
             (2, 6, (229, 192, 123)), (3, 11, (171, 178, 191)), (2, 7, (198, 120, 221))]
    for i, (x0, x1, c) in enumerate(lines):
        if Y0 + 1 + i * 1.5 < Y1:
            fill(px, x0, Y0 + 1 + int(i * 1.5), x1, Y0 + 2 + int(i * 1.5), c)


def sheet_app(px):
    fill(px, X0, Y0, X1, Y1, (250, 250, 250))
    fill(px, X0, Y0, X1, Y0 + 1, (33, 140, 82))
    for y in range(Y0 + 2, Y1, 2):
        fill(px, X0, y, X1, y + 1, (214, 218, 222))
    for x in (4, 8, 11):
        fill(px, x, Y0 + 1, x + 1, Y1, (214, 218, 222))


def browser(px):
    fill(px, X0, Y0, X1, Y1, (246, 247, 249))
    fill(px, X0, Y0, X1, Y0 + 1, (205, 210, 216))
    fill(px, 3, Y0 + 2, 13, Y0 + 3, (66, 103, 178))
    fill(px, 3, Y0 + 4, 8, Y0 + 8, (130, 180, 220))
    for y in (Y0 + 4, Y0 + 6):
        fill(px, 9, y, 13, y + 1, (150, 156, 164))
    fill(px, 3, Y0 + 9, 12, Y0 + 10 if Y0 + 10 <= Y1 else Y1, (150, 156, 164))


def video_call(px):
    fill(px, X0, Y0, X1, Y1, (40, 42, 46))
    tiles = [(1, 3), (8, 3), (1, 8), (8, 8)]
    colors = [(70, 90, 120), (90, 110, 80), (120, 90, 80), (80, 80, 110)]
    for (x0, y0), c in zip(tiles, colors):
        fill(px, x0 + 1, y0, x0 + 6, y0 + 4, c)
        fill(px, x0 + 3, y0 + 1, x0 + 4 + 1, y0 + 3, (226, 190, 160))   # a face


def map_app(px):
    fill(px, X0, Y0, X1, Y1, (196, 224, 180))
    fill(px, X0, Y0, 5, Y1, (150, 196, 232))                      # sea
    for x in range(5, 15):
        px[x, 8] = (250, 250, 250, 255)                           # road
    for y in range(Y0, Y1):
        px[10, y] = (246, 206, 90, 255)
    px[10, 8] = (230, 70, 60, 255)                                # pin


def slides(px):
    fill(px, X0, Y0, X1, Y1, (236, 238, 241))
    fill(px, 3, Y0 + 1, 11, Y0 + 2, (40, 60, 110))
    for i, h in enumerate((3, 5, 4, 6)):
        fill(px, 4 + 2 * i, Y1 - 1 - h, 5 + 2 * i, Y1 - 1, (230, 120, 60) if i == 3 else (90, 130, 200))


def mail(px):
    fill(px, X0, Y0, X1, Y1, (252, 252, 252))
    fill(px, X0, Y0, 4, Y1, (225, 230, 238))
    for y in range(Y0 + 1, Y1 - 1, 2):
        fill(px, 5, y, 13 - (y % 3), y + 1, (150, 156, 164))
    px[6, Y0 + 1] = (50, 120, 230, 255)


SCREENS = [desktop, code, sheet_app, browser, video_call, map_app, slides, mail]


def screen(draw):
    img = blank()
    draw(img.load())
    return img


# ---------- lid: grey aluminium with an Apple logo ----------
APPLE = [
    "........",
    ".....#..",
    "....#...",
    ".##.###.",
    "#######.",
    "######..",
    "######..",
    "#######.",
    ".######.",
    "..#..#..",
]


def lid():
    rng = random.Random(11)
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            edge = x in (0, 15) or y in (0, 15)
            base = LID_EDGE if edge else LID
            d = rng.randint(-2, 2)
            px[x, y] = tuple(max(0, min(255, v + d)) for v in base) + (255,)
    ox, oy = 4, 3
    for j, row in enumerate(APPLE):
        for i, ch in enumerate(row):
            if ch == "#":
                px[ox + i, oy + j] = LOGO + (255,)
    return img


screens = [screen(d) for d in SCREENS]
lid_img = lid()
overlay = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
for i, img in enumerate(screens[:7]):
    overlay.paste(img, (16 * i, 0))
for tx in range(4):
    for ty in range(4):
        overlay.paste(lid_img, (192 + 16 * tx, 16 * ty))
overlay.save(HERE / "kz_overlay.png")
screens[7].save(HERE / "meditative.png")

# Preview atlas: the eight screens in a row, then the lid.
atlas = Image.new("RGBA", (16 * 9, 16), (0, 0, 0, 0))
for i, img in enumerate(screens):
    atlas.paste(img, (16 * i, 0))
atlas.paste(lid_img, (128, 0))
atlas.save(HERE / "preview_atlas.png")

# ---------- preview models: a 16x16 painting, 1 pixel thick ----------
lid_face = {"uv": [128, 0], "uv_size": [16, 16]}
edge = {"uv": [129, 1], "uv_size": [1, 1]}
geos = []
for i in range(8):
    geos.append({
        "description": {"identifier": f"geometry.laptop_{i}", "texture_width": 144, "texture_height": 16},
        "bones": [{"name": "painting", "pivot": [0, 0, 0], "cubes": [{
            "origin": [-8, 0, -8], "size": [16, 16, 1],
            "uv": {"south": {"uv": [16 * i, 0], "uv_size": [16, 16]}, "north": lid_face,
                   "east": edge, "west": edge, "up": edge, "down": edge},
        }]}],
    })
geos.append({
    "description": {"identifier": "geometry.deck", "texture_width": 144, "texture_height": 16},
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


desk_row = []
for x in range(-32, 33, 16):
    desk_row.append(block(x, -16, 0, DESK))
desk_row += laptop(0, -32, 0, 0) + laptop(1, 0, 0, 0) + laptop(2, 32, 0, 0)

all_screens = []
for i in range(8):
    x = -56 + 16 * i
    all_screens += [block(x, 0, 0, WALL), painting(i, x, 0, 16)]

office = []
for x in range(-32, 33, 16):
    for z in (0, 16):
        office.append(block(x, -16, z, DESK))
office += laptop(3, -32, 0, 0) + laptop(4, 0, 0, 0) + laptop(5, 32, 0, 0)
office += laptop(6, -32, 0, 16, 180) + laptop(7, 0, 0, 16, 180) + laptop(0, 32, 0, 16, 180)

sheet = {
    "title": "筆電：一格大小的畫換成螢幕，畫的背面換成灰色加蘋果標誌（草稿）",
    "columns": 2, "panelWidth": 560, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "八種一格大小的畫，全部是螢幕（隨機到哪一幅都是）", "camera": {"azimuth": 0, "elevation": 0, "size": 72, "target": [0, 8, 8]},
         "objects": all_screens},
        {"label": "桌上的筆電（前面）", "camera": {"azimuth": 20, "elevation": 22, "size": 56, "target": [0, 6, 0]},
         "objects": desk_row},
        {"label": "從背面看：灰色上蓋加蘋果標誌", "camera": {"azimuth": 200, "elevation": 18, "size": 56, "target": [0, 6, 0]},
         "objects": desk_row},
        {"label": "辦公桌：面對面的兩排", "camera": {"azimuth": 35, "elevation": 35, "size": 80, "target": [0, 2, 8]},
         "objects": office},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote kz_overlay.png, meditative.png, preview files")
