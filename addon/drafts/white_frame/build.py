"""Build the white item frame: the item frame texture.

Run from the repository root:
    python3 addon/drafts/white_frame/build.py

Resource pack only: itemframe_background.png replaces
textures/blocks/itemframe_background.png, so every (non-glowing) item frame
is white. On a wall it is a clean white frame; laid flat on a table with
food in it, it is a white square plate. The vanilla export is simply the
item frame, with the item still in it.

Like the glow frame, Bedrock draws the whole frame, border and background,
from this one 16x16 texture on a model built into the game, and keeps the
raised border. The outer 2 pixels are the rim; a faint square line inside
reads as a mat on a wall and as the well of a plate on a table.
"""
import json
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/white_frame"

RIM_EDGE = (212, 213, 209)
RIM = (238, 238, 235)
FIELD = (247, 247, 245)
WELL_LINE = (230, 230, 226)
CENTRE = (251, 251, 249)


def frame_texture():
    img = Image.new("RGBA", (16, 16), FIELD + (255,))
    px = img.load()
    for y in range(16):
        for x in range(16):
            ring = min(x, y, 15 - x, 15 - y)
            if ring == 0:
                c = RIM_EDGE
            elif ring == 1:
                c = RIM
            elif ring == 3:
                c = WELL_LINE
            elif ring >= 4:
                c = CENTRE
            else:
                c = FIELD
            px[x, y] = c + (255,)
    return img


frame_texture().save(HERE / "itemframe_background.png")

# ---------- placeholder food, drawn here only for the preview ----------


def sprite(draw):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw(img.load())
    return img


def onigiri(px):
    for y in range(3, 14):
        half = (y - 2) * 0.6 + 1
        for x in range(16):
            if abs(x - 7.5) <= half and y <= 13:
                px[x, y] = (246, 246, 240, 255)
    for y in range(10, 14):
        for x in range(5, 11):
            px[x, y] = (40, 52, 44, 255)


def omelette(px):
    for y in range(16):
        for x in range(16):
            if ((x - 7.5) / 6.5) ** 2 + ((y - 8) / 4.2) ** 2 <= 1:
                px[x, y] = (238, 196, 72, 255)
    for x in range(6, 11):
        px[x, 7] = (196, 48, 40, 255)
        px[x - 1, 8] = (196, 48, 40, 255)


def dango(px):
    for x in range(1, 15):
        px[x, 8] = (176, 140, 90, 255)
    for cx, color in ((4, (240, 170, 180)), (8, (246, 246, 240)), (12, (150, 190, 110))):
        for y in range(16):
            for x in range(16):
                if math.hypot(x - cx, y - 8) <= 2.3:
                    px[x, y] = color + (255,)


FOODS = {"onigiri": onigiri, "omelette": omelette, "dango": dango}
for name, draw in FOODS.items():
    sprite(draw).save(HERE / f"food_{name}.png")

# ---------- preview models ----------
edge = {"uv": [0, 0], "uv_size": [1, 1]}


def cube(origin, size, front, back=edge):
    faces = {d: edge for d in ("east", "west", "up", "down")}
    faces["south"] = front
    faces["north"] = back
    return {"origin": origin, "size": size, "uv": faces}


# The frame, approximating the vanilla model like the screen draft: a 12 x 12
# outline with a raised 1-pixel border, against the north side of its block.
frame_cubes = [
    cube([-5, 3, -8], [10, 10, 0.5], {"uv": [3, 3], "uv_size": [10, 10]}),
    cube([-6, 13, -8], [12, 1, 1], {"uv": [2, 1], "uv_size": [12, 1]}),
    cube([-6, 2, -8], [12, 1, 1], {"uv": [2, 14], "uv_size": [12, 1]}),
    cube([-6, 3, -8], [1, 10, 1], {"uv": [1, 3], "uv_size": [1, 10]}),
    cube([5, 3, -8], [1, 10, 1], {"uv": [14, 3], "uv_size": [1, 10]}),
]
# An item lying on the frame's background: a flat 8 x 8 picture.
item_cubes = [cube([-4, 4, -7.4], [8, 8, 0.01], {"uv": [0, 0], "uv_size": [16, 16]},
                   back={"uv": [0, 0], "uv_size": [16, 16]})]
geo = {"format_version": "1.12.0", "minecraft:geometry": [
    {"description": {"identifier": "geometry.frame_preview", "texture_width": 16, "texture_height": 16},
     "bones": [{"name": "frame", "pivot": [0, 0, 0], "cubes": frame_cubes}]},
    {"description": {"identifier": "geometry.item_preview", "texture_width": 16, "texture_height": 16},
     "bones": [{"name": "item", "pivot": [0, 0, 0], "cubes": item_cubes}]},
]}
(HERE / "preview.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
WALL_DARK = {"up": "#6f7a83", "south": "#5f6a73", "north": "#5f6a73", "east": "#525c64", "west": "#525c64", "down": "#454e55"}
TABLE = {"up": "#7a5a3c", "south": "#654a31", "north": "#654a31", "east": "#574029", "west": "#574029", "down": "#4a3623"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def on_wall(x, y, z, food=None):
    """Hanging on the south face of the block at (x, y, z - 16)."""
    objs = [{"type": "geo", "geo": f"{REL}/preview.geo.json", "identifier": "geometry.frame_preview",
             "texture": f"{REL}/itemframe_background.png", "position": [x, y, z]}]
    if food:
        objs.append({"type": "geo", "geo": f"{REL}/preview.geo.json", "identifier": "geometry.item_preview",
                     "texture": f"{REL}/food_{food}.png", "position": [x, y, z]})
    return objs


def on_table(x, y, z, food=None, turn=0):
    """Lying face up in the block at (x, y, z), on top of the block below."""
    objs = []
    for o in on_wall(x, y, z, food):
        o["rotation"] = [-90, turn, 0]
        objs.append(o)
    return objs


wall_frames = [block(x, 0, 0, WALL) for x in (-24, -8, 8, 24)] + on_wall(-16, 0, 16) + on_wall(0, 0, 16, "onigiri") \
    + on_wall(16, 0, 16, "omelette")
dark_wall = [block(x, 0, 0, WALL_DARK) for x in (-8, 8)] + on_wall(0, 0, 16)
table = []
for x in (-16, 0, 16):
    for z in (0, 16):
        table.append(block(x, -16, z, TABLE))
        table.append(block(x, -32, z, FLOOR))
table += on_table(-16, 0, 0, "onigiri") + on_table(0, 0, 0, "omelette") + on_table(16, 0, 0, "dango") \
    + on_table(-16, 0, 16, "dango") + on_table(0, 0, 16) + on_table(16, 0, 16, "onigiri")

sheet = {
    "title": "白色物品展示框（草稿，食物只是示意）",
    "columns": 3, "panelWidth": 380, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "掛在牆上：空的、放東西", "camera": {"azimuth": 0, "elevation": 0, "size": 44, "target": [0, 8, 8]},
         "objects": wall_frames},
        {"label": "斜看：邊框的立體", "camera": {"azimuth": 50, "elevation": 25, "size": 22, "target": [-16, 8, 9]},
         "objects": wall_frames},
        {"label": "深色牆上", "camera": {"azimuth": 0, "elevation": 0, "size": 20, "target": [0, 8, 8]},
         "objects": dark_wall},
        {"label": "平放在桌上當盤子", "camera": {"azimuth": 30, "elevation": 40, "size": 60, "target": [0, 0, 8]},
         "objects": table},
        {"label": "盤子近看", "camera": {"azimuth": 20, "elevation": 35, "size": 16, "target": [0, 1, 0]},
         "objects": table},
        {"label": "從上往下看", "camera": {"azimuth": 0, "elevation": 89, "size": 54, "target": [0, 0, 8]},
         "objects": table},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote itemframe_background.png, food sprites, preview.geo.json, preview.json")
