"""Build the office drawer draft: a texture that replaces the light gray shulker box.

Run from the repository root:
    python3 addon/drafts/drawer/build.py

Resource pack only: the files replace textures/entity/shulker/shulker_silver.png
and textures/blocks/shulker_top_silver.png (Bedrock calls light gray "silver"),
so every light gray shulker box looks like a steel office pedestal: three
drawers, each with a recessed handle, and a lock at the top right. Decided by the author 2026-11-03: the light gray box.
The vanilla export is simply the light gray shulker box.

Same model and rules as the locker (addon/drafts/locker/build.py): the front
goes on the lid's top face, which turns to face the player who places it;
the lid's side rows that overlap the base stay transparent.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/drawer"

FRONT = (204, 207, 210)
FRONT_LOW = (192, 196, 199)
SEAM = (128, 133, 138)
HANDLE = (70, 74, 80)
HANDLE_LIP = (226, 228, 230)
LOCK = (176, 180, 184)
LOCK_DARK = (88, 92, 98)
SIDE = (196, 199, 203)
SIDE_EDGE = (168, 172, 177)
INSIDE = (118, 122, 128)


def grain(seed):
    rng = random.Random(seed)
    streaks = {}
    for _ in range(9):
        y, x0 = rng.randrange(16), rng.randrange(14)
        shade = rng.choice((-4, -3, 3, 4))
        for x in range(x0, min(16, x0 + rng.randint(3, 6))):
            streaks[(x, y)] = shade
    return rng, streaks


def steel(color, x, y, rng, streaks):
    d = rng.randint(-2, 2) + streaks.get((x, y), 0)
    return tuple(max(0, min(255, c + d)) for c in color)


def front_face():
    """16 x 16 front, row 0 at the top: three drawers at rows 1-4, 6-9 and 11-14."""
    rng, streaks = grain(11)
    f = [[steel(FRONT, x, y, rng, streaks) for x in range(16)] for y in range(16)]
    for i in range(16):
        f[0][i] = f[15][i] = f[i][0] = f[i][15] = SEAM
    for y in (5, 10):                       # the gaps between the drawers
        for x in range(16):
            f[y][x] = SEAM
    for top in (1, 6, 11):
        for x in range(1, 15):              # a faint shadow at each drawer's bottom
            f[top + 3][x] = steel(FRONT_LOW, x, top + 3, rng, {})
        for x in range(5, 11):              # recessed handle: a dark slot with a light lip
            f[top][x] = HANDLE_LIP
            f[top + 1][x] = HANDLE
    f[2][13] = LOCK                         # lock cylinder, top right
    f[2][12] = LOCK
    f[3][12] = LOCK
    f[3][13] = LOCK_DARK
    return f


def side_face(seed):
    rng, streaks = grain(seed)
    f = [[steel(SIDE, x, y, rng, streaks) for x in range(16)] for y in range(16)]
    for i in range(16):
        f[0][i] = f[15][i] = f[i][0] = f[i][15] = SIDE_EDGE
    return f


def make_texture():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    px = img.load()

    def paint(x0, y0, f, rows=range(16), dy=0):
        for y in rows:
            for x in range(16):
                px[x0 + x, y0 + y - dy] = f[y][x] + (255,)

    def fill(x0, y0, w, h, color):
        for y in range(h):
            for x in range(w):
                px[x0 + x, y0 + y] = color + (255,)

    paint(16, 0, front_face())                 # lid top: the drawer fronts
    fill(32, 0, 16, 16, INSIDE)                # lid underside, hidden
    fill(16, 28, 16, 16, INSIDE)               # base top, hidden
    paint(32, 28, side_face(19))               # base bottom: the back
    for side in range(4):
        f = side_face(12 + side)
        u = side * 16
        paint(u, 16, f, rows=range(8))             # lid side: front half
        paint(u, 44, f, rows=range(8, 16), dy=8)   # base side: back half
    fill(0, 52, 24, 12, INSIDE)                # head: only a dyed shulker mob uses it
    return img


tex = make_texture()
tex.save(HERE / "shulker_silver.png")
tex.crop((32, 28, 48, 44)).save(HERE / "shulker_top_silver.png")   # breaking particles

# ---------- preview sheet (the locker's preview model) ----------
GEO = "/addon/drafts/locker/shulker_preview.geo.json"
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}
DESK = {"up": "#e9e4da", "south": "#d6d0c4", "north": "#d6d0c4", "east": "#c4beb2", "west": "#c4beb2", "down": "#b0aa9e"}


def drawer(x, y, z):
    return {"type": "geo", "geo": GEO, "texture": f"{REL}/shulker_silver.png", "rotation": [90, 0, 0],
            "position": [x, y, z]}


def block(x, y, z, color, size=(16, 16, 16)):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": list(size)}


def office():
    """Two desks along a wall, each with a pedestal under one end."""
    objs = []
    for x in (-24, -8, 8, 24):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, -16, FLOOR), block(x, 0, -16, WALL), block(x, 16, -16, WALL)]
    for x in (-24, -8, 8, 24):                              # desk tops: a thin slab at 16
        objs.append({"type": "block", "color": DESK, "origin": [x - 8, 16, -8], "size": [16, 2, 16]})
    objs += [drawer(-24, 0, 0), drawer(24, 0, 0)]
    return objs


sheet = {
    "title": "辦公室抽屜櫃：淺灰色界伏蚌盒換材質（草稿）",
    "columns": 3, "panelWidth": 380, "panelHeight": 320, "background": "#e8edf1",
    "panels": [
        {"label": "單一個（正面朝向放置的人）", "camera": {"azimuth": 30, "elevation": 25, "size": 30, "target": [0, 7, 0]},
         "objects": [block(0, -16, 0, FLOOR), drawer(0, 0, 0)]},
        {"label": "正面", "camera": {"azimuth": 0, "elevation": 0, "size": 20, "target": [0, 8, 0]},
         "objects": [block(0, -16, 0, FLOOR), drawer(0, 0, 0)]},
        {"label": "辦公桌下", "camera": {"azimuth": 25, "elevation": 15, "size": 80, "target": [0, 10, -4]},
         "objects": office()},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote shulker_silver.png, shulker_top_silver.png, preview.json")
