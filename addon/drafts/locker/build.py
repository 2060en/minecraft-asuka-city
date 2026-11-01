"""Build the locker draft: a texture that replaces the white shulker box.

Run from the repository root:
    python3 addon/drafts/locker/build.py

Resource pack only: the file replaces textures/entity/shulker/shulker_white.png,
so every white shulker box looks like a steel coin locker of the kind found at
stations and airports. The vanilla export is simply the white shulker box.

The vanilla shulker model (geometry.shulker.v1.8) is a 16x8x16 base and a
16x12x16 lid on box UVs, base at (0, 28) and lid at (0, 0) of a 64x64 texture.
The lid's sides cover heights 4-16 and the base's sides 0-8, so they overlap
at 4-8; the lid rows for that band are left transparent so the two faces do
not fight. The door is painted on all four sides because a shulker box
standing on the floor always has the same orientation; the side you see from
the front depends on which way the wall faces.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/locker"

SEAM = (150, 156, 162, 255)
DOOR = (236, 238, 239, 255)
DOOR_LOW = (222, 225, 227, 255)
VENT = (196, 201, 205, 255)
PLATE = (52, 60, 72, 255)
PLATE_TEXT = (226, 230, 234, 255)
LOCK = (184, 190, 196, 255)
LOCK_DARK = (92, 98, 104, 255)
LAMP = (222, 92, 60, 255)
TOP = (226, 229, 232, 255)
TOP_EDGE = (200, 205, 209, 255)
INSIDE = (120, 126, 132, 255)
CLEAR = (0, 0, 0, 0)


def door_face():
    """16 x 16 locker door, row 0 at the top."""
    f = [[DOOR] * 16 for _ in range(16)]
    for i in range(16):
        f[0][i] = f[15][i] = f[i][0] = f[i][15] = SEAM
    for x in range(1, 15):
        f[14][x] = DOOR_LOW
    # Number plate, top left, with a light line for the number.
    for y in (2, 3, 4):
        for x in range(2, 7):
            f[y][x] = PLATE
    for x in (3, 4, 5):
        f[3][x] = PLATE_TEXT
    # Vent slits, bottom left.
    for y in (10, 12):
        for x in range(3, 9):
            f[y][x] = VENT
    # Lock unit on the right: coin slot, keyhole, and a small lamp.
    for y in range(6, 12):
        for x in (11, 12, 13):
            f[y][x] = LOCK
    f[7][12] = LOCK_DARK          # coin slot
    f[9][12] = LOCK_DARK          # keyhole
    f[10][12] = LOCK_DARK
    f[11][12] = LAMP              # in-use lamp
    return f


def make_texture():
    img = Image.new("RGBA", (64, 64), CLEAR)
    px = img.load()
    door = door_face()

    def fill(x0, y0, w, h, color):
        for y in range(h):
            for x in range(w):
                px[x0 + x, y0 + y] = color

    # Lid (box UV at 0, 0; 16x12x16): top (16,0), bottom (32,0), sides at row 16.
    fill(16, 0, 16, 16, TOP)
    for i in range(16):
        px[16 + i, 0] = px[16 + i, 15] = px[16, i] = px[31, i] = TOP_EDGE
    fill(32, 0, 16, 16, INSIDE)
    # Base (box UV at 0, 28; 16x8x16): top (16,28), bottom (32,28), sides at row 44.
    fill(16, 28, 16, 16, INSIDE)
    fill(32, 28, 16, 16, TOP_EDGE)
    for side in range(4):
        u = side * 16
        for y in range(8):
            for x in range(16):
                px[u + x, 16 + y] = door[y][x]          # lid side: door rows 0-7
                px[u + x, 44 + y] = door[8 + y][x]      # base side: door rows 8-15
        # Lid side rows 24-27 (heights 4-8) stay transparent.
    # Head (box UV at 0, 52; 6x6x6) is only used by a dyed shulker mob.
    fill(0, 52, 24, 12, INSIDE)
    return img


def box_uv(u, v, w, h, d):
    """Per-face UVs for a box-UV cube, for the preview tool."""
    def f(x, y, a, b):
        return {"uv": [x, y], "uv_size": [a, b]}
    return {
        "up": f(u + d, v, w, d), "down": f(u + d + w, v, w, d),
        "east": f(u, v + d, d, h), "north": f(u + d, v + d, w, h),
        "west": f(u + d + w, v + d, d, h), "south": f(u + 2 * d + w, v + d, w, h),
    }


tex = make_texture()
tex.save(HERE / "shulker_white.png")
# textures/blocks/shulker_top_white.png: used for the breaking particles;
# reuse the locker's top so they match.
tex.crop((16, 0, 32, 16)).save(HERE / "shulker_top_white.png")
preview_geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.shulker_box_preview", "texture_width": 64, "texture_height": 64},
    "bones": [
        {"name": "base", "pivot": [0, 0, 0], "cubes": [{"origin": [-8, 0, -8], "size": [16, 8, 16], "uv": box_uv(0, 28, 16, 8, 16)}]},
        {"name": "lid", "pivot": [0, 0, 0], "cubes": [{"origin": [-8, 4, -8], "size": [16, 12, 16], "uv": box_uv(0, 0, 16, 12, 16)}]},
    ],
}]}
(HERE / "shulker_preview.geo.json").write_text(json.dumps(preview_geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}


def locker(x, y, z):
    return {"type": "geo", "geo": f"{REL}/shulker_preview.geo.json", "texture": f"{REL}/shulker_white.png",
            "position": [x, y, z]}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def bank(cols, rows):
    """Lockers in front of a wall that runs east-west along z = -16."""
    objs = []
    xs = [16 * (i - (cols - 1) / 2) for i in range(cols)]
    for x in [xs[0] - 16] + xs + [xs[-1] + 16]:
        for y in range(0, 16 * (rows + 1), 16):
            objs.append(block(x, y, -16, WALL))
        objs.append(block(x, -16, 0, FLOOR))
        objs.append(block(x, -16, -16, FLOOR))
    for x in xs:
        for r in range(rows):
            objs.append(locker(x, 16 * r, 0))
    return objs


sheet = {
    "title": "置物櫃：白色界伏蚌盒換材質（草稿）",
    "columns": 3, "panelWidth": 380, "panelHeight": 320, "background": "#e8edf1",
    "panels": [
        {"label": "單一個", "camera": {"azimuth": 30, "elevation": 25, "size": 30, "target": [0, 7, 0]},
         "objects": [block(0, -16, 0, FLOOR), locker(0, 0, 0)]},
        {"label": "靠牆排成 4 列 × 3 層", "camera": {"azimuth": 25, "elevation": 15, "size": 96, "target": [0, 22, -4]},
         "objects": bank(4, 3)},
        {"label": "正面", "camera": {"azimuth": 0, "elevation": 0, "size": 60, "target": [0, 24, 0]},
         "objects": bank(4, 3)},
        {"label": "門的近看", "camera": {"azimuth": 0, "elevation": 0, "size": 20, "target": [-8, 8, 0]},
         "objects": bank(4, 3)},
        {"label": "從側面看：側面也是門", "camera": {"azimuth": 70, "elevation": 15, "size": 96, "target": [0, 22, -4]},
         "objects": bank(4, 3)},
        {"label": "從上面看", "camera": {"azimuth": 20, "elevation": 60, "size": 96, "target": [0, 22, -4]},
         "objects": bank(4, 3)},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote shulker_white.png, shulker_top_white.png, shulker_preview.geo.json, preview.json")
