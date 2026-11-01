"""Build the general-purpose small screen draft: glow item frame textures.

Run from the repository root:
    python3 addon/drafts/screen/build.py

Resource pack only: the chosen design replaces textures/blocks/glow_item_frame.png,
so an empty glow item frame looks like a small screen for vending machines,
ticket machines, locker control panels and so on. A special picture goes on
top by putting an Image map into the frame. The vanilla export is simply the
glow item frame.

Bedrock draws the whole frame, border and background, from this one 16x16
texture (the vanilla one has a 1-pixel dark edge and a leather background).
The exact model is built into the game, so the design keeps a 2-pixel bezel
that reads as a bezel however the border samples the edge. Whether the empty
frame stays bright in the dark needs a test; if not, a light block (invisible,
vanilla) next to it does the job.

Three candidates for the default picture:
    a  off: a dark screen with a reflection
    b  standby: a blue screen with a title bar and a few menu lines
    c  touch menu: a dark screen with four coloured buttons
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/screen"

BEZEL = (27, 29, 32)
BEZEL_EDGE = (44, 47, 52)


def screen(kind):
    img = Image.new("RGBA", (16, 16), BEZEL + (255,))
    px = img.load()
    for i in range(16):
        px[i, 0] = px[i, 15] = px[0, i] = px[15, i] = BEZEL_EDGE + (255,)

    def put(x, y, c):
        px[x, y] = c + (255,)

    inner = [(x, y) for y in range(2, 14) for x in range(2, 14)]
    if kind == "a":
        for x, y in inner:
            put(x, y, (35, 39, 44))
        # Two diagonal glints from the top left.
        for i in range(2, 9):
            put(i + 1, 12 - i + 2 - 3, (58, 64, 72))
        for i in range(2, 6):
            put(i + 4, 12 - i - 1, (50, 56, 63))
    elif kind == "b":
        for x, y in inner:
            put(x, y, (47, 111, 179))
        for x in range(2, 14):
            for y in (2, 3):
                put(x, y, (36, 87, 142))
        put(3, 2, (232, 240, 248))
        for y, (x0, x1) in ((5, (3, 11)), (7, (3, 9)), (9, (3, 10))):
            for x in range(x0, x1):
                put(x, y, (226, 236, 246))
        for y in (11, 12):
            for x in range(9, 13):
                put(x, y, (242, 193, 78))
    elif kind == "c":
        for x, y in inner:
            put(x, y, (30, 42, 53))
        tiles = {(3, 3): (58, 167, 118), (8, 3): (224, 138, 60),
                 (3, 8): (59, 130, 196), (8, 8): (208, 87, 75)}
        for (x0, y0), c in tiles.items():
            for y in range(y0, y0 + 5):
                for x in range(x0, x0 + 5):
                    put(x, y, c)
    return img


for k in "abc":
    screen(k).save(HERE / f"glow_item_frame_{k}.png")

# Preview model: a 12 x 12 panel, 1 pixel thick, against the north side of
# its block (the side of the block the frame hangs on). The real frame is
# built into the game; this only approximates it.
edge = {"uv": [0, 0], "uv_size": [1, 1]}
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.frame_preview", "texture_width": 16, "texture_height": 16},
    "bones": [{"name": "frame", "pivot": [0, 0, 0], "cubes": [{
        "origin": [-6, 2, -8], "size": [12, 12, 1],
        "uv": {"south": {"uv": [0, 0], "uv_size": [16, 16]}, "north": edge,
               "east": edge, "west": edge, "up": edge, "down": edge},
    }]}],
}]}
(HERE / "frame_preview.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}
VENDING = {"up": "#e9ecee", "south": "#d6dadd", "north": "#d6dadd", "east": "#c3c8cc", "west": "#c3c8cc", "down": "#aab0b5"}
VENDING_RED = {"up": "#d2463e", "south": "#c13c35", "north": "#c13c35", "east": "#a8332d", "west": "#a8332d", "down": "#8e2a25"}
PANEL = {"up": "#a9b0b7", "south": "#9aa1a8", "north": "#9aa1a8", "east": "#8a9198", "west": "#8a9198", "down": "#7a8188"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def frame(x, y, z, kind):
    """A frame hanging on the south face of the block at (x, y, z - 16)."""
    return {"type": "geo", "geo": f"{REL}/frame_preview.geo.json", "texture": f"{REL}/glow_item_frame_{kind}.png",
            "position": [x, y, z]}


def locker(x, y, z):
    return {"type": "geo", "geo": "/addon/drafts/locker/shulker_preview.geo.json",
            "texture": "/addon/drafts/locker/shulker_white.png", "rotation": [90, 0, 0], "position": [x, y, z]}


def options_wall():
    objs = []
    for x in (-24, -8, 8, 24):
        objs.append(block(x, 0, 0, WALL))
    for x, k in ((-16, "a"), (0, "b"), (16, "c")):
        objs.append({"type": "geo", "geo": f"{REL}/frame_preview.geo.json",
                     "texture": f"{REL}/glow_item_frame_{k}.png", "position": [x, 0, 16]})
    return objs


def vending(kind):
    objs = [block(0, -16, 0, FLOOR), block(0, -16, 16, FLOOR), block(16, -16, 0, FLOOR), block(16, -16, 16, FLOOR)]
    for x, body in ((0, VENDING_RED), (16, VENDING)):
        objs += [block(x, 0, 0, body), block(x, 16, 0, body)]
        objs.append(frame(x, 16, 16, kind))
    return objs


def locker_panel(kind):
    objs = []
    for x in (-24, -8, 8, 24):
        objs.append(block(x, -16, 0, FLOOR))
        for y in (0, 16, 32):
            objs.append(block(x, y, -16, WALL))
            if x == -8 and y == 16:
                objs.append(block(x, y, 0, PANEL))
                objs.append(frame(x, y, 16, kind))
            else:
                objs.append(locker(x, y, 0))
    return objs


def ticket_machines(kind):
    objs = []
    for x in (-16, 0, 16):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, 16, FLOOR), block(x, 0, -16, WALL), block(x, 16, -16, WALL)]
        objs += [block(x, 0, 0, PANEL)]
        objs.append(frame(x, 0, 16, kind))
    return objs


panels = [
    {"label": "a 關機｜b 待機｜c 觸控選單", "camera": {"azimuth": 0, "elevation": 0, "size": 40, "target": [0, 8, 8]},
     "objects": options_wall()},
]
for k, name in (("a", "a 關機"), ("b", "b 待機"), ("c", "c 觸控選單")):
    panels.append({"label": f"販賣機上（{name}）", "camera": {"azimuth": 25, "elevation": 12, "size": 54, "target": [8, 14, 6]},
                   "objects": vending(k)})
panels.append({"label": "置物櫃的操作面板（b）", "camera": {"azimuth": 20, "elevation": 12, "size": 80, "target": [0, 22, 0]},
               "objects": locker_panel("b")})
panels.append({"label": "售票機（c）", "camera": {"azimuth": 25, "elevation": 20, "size": 60, "target": [0, 8, 6]},
               "objects": ticket_machines("c")})

sheet = {"title": "萬用小螢幕：發光物品框架換材質（草稿，三種預設畫面）", "columns": 3, "panelWidth": 380, "panelHeight": 300,
         "background": "#e8edf1", "panels": panels}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote glow_item_frame_a/b/c.png, frame_preview.geo.json, preview.json")
