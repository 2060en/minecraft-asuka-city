"""Build the general-purpose small screen: the glow item frame texture.

Run from the repository root:
    python3 addon/drafts/screen/build.py

Resource pack only: glow_item_frame.png replaces textures/blocks/glow_item_frame.png,
so an empty glow item frame looks like a small screen for vending machines,
ticket machines, locker control panels and so on. A special picture goes on
top by putting an Image map into the frame. The vanilla export is simply the
glow item frame.

Decided 2026-11-01: the standby picture (option b of the first draft: a blue
screen with a title bar, menu lines and a yellow button) inside a black
border. The frame keeps the vanilla model's raised border, which a resource
pack cannot change anyway; only its colour changes.

Bedrock draws the whole frame, border and background, from this one 16x16
texture, and the exact model is built into the game. So the outer 2 pixels
are black, whatever part of them the border uses, and the picture keeps its
details inside pixels 3-12 in case the background shows only the middle.
Whether the empty frame stays bright in the dark needs a test; if not, a
light block (invisible, vanilla) next to it does the job.

Second version (2026-11-03): the raised border is drawn by the game with the
birch planks texture, which stays (other birch would change with it), so the
black edge looked like a second frame inside the wooden one. The author
asked to try the edge in the same colour as the border: the black edge is
now birch-coloured, so the screen sits straight in the wooden frame.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/screen"

BIRCH = [(214, 199, 139), (205, 189, 130), (196, 180, 122)]   # the vanilla birch planks range
BIRCH_EDGE = (178, 161, 107)
BLUE = (47, 111, 179)
BAR = (36, 87, 142)
TEXT = (226, 236, 246)
DOT = (232, 240, 248)
BUTTON = (242, 193, 78)


def screen():
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    rng = random.Random(7)
    for y in range(16):
        for x in range(16):
            px[x, y] = rng.choice(BIRCH) + (255,)

    def put(x, y, c):
        px[x, y] = c + (255,)

    for i in range(16):
        for j in (0, 15):
            put(i, j, BIRCH_EDGE)
            put(j, i, BIRCH_EDGE)
    for y in range(2, 14):
        for x in range(2, 14):
            put(x, y, BLUE)
    for y in (3, 4):
        for x in range(2, 14):
            put(x, y, BAR)
    put(4, 3, DOT)
    for y, (x0, x1) in ((6, (4, 11)), (8, (4, 9)), (10, (4, 8))):
        for x in range(x0, x1):
            put(x, y, TEXT)
    for y in (10, 11):
        for x in range(9, 12):
            put(x, y, BUTTON)
    return img


# The second version waits for the author's approval in its own file;
# addon/pack/build.py still takes glow_item_frame.png, the first version.
screen().save(HERE / "glow_item_frame_v2.png")
for old in ("glow_item_frame_a.png", "glow_item_frame_b.png", "glow_item_frame_c.png"):
    (HERE / old).unlink(missing_ok=True)

# Preview model, approximating the vanilla frame: a 12 x 12 outline, a
# 1-pixel border that stands 1 pixel off the wall, and a 10 x 10 background
# half a pixel deep. It hangs on the north side of its block. How the game
# maps the texture onto its own model needs a test; here the background
# shows the middle 10 x 10, and the border is drawn with the birch planks
# texture, as the game does.
black = {"uv": [0, 0], "uv_size": [16, 16]}


def cube(origin, size, front):
    faces = {d: black for d in ("north", "east", "west", "up", "down")}
    faces["south"] = front
    return {"origin": origin, "size": size, "uv": faces}


screen_cubes = [cube([-5, 3, -8], [10, 10, 0.5], {"uv": [3, 3], "uv_size": [10, 10]})]   # background
border_cubes = [
    cube([-6, 13, -8], [12, 1, 1], black),                                   # border: top
    cube([-6, 2, -8], [12, 1, 1], black),                                    # bottom
    cube([-6, 3, -8], [1, 10, 1], black),                                    # west
    cube([5, 3, -8], [1, 10, 1], black),                                     # east
]
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.frame_preview", "texture_width": 16, "texture_height": 16},
    "bones": [{"name": "screen", "pivot": [0, 0, 0], "cubes": screen_cubes},
              {"name": "border", "pivot": [0, 0, 0], "cubes": border_cubes}],
}]}
# The border is drawn with the vanilla birch planks, cached by addon/pack/build.py
# (or addon/drafts/props/build.py) in addon/build/vanilla/.
BIRCH_PLANKS = "/addon/build/vanilla/textures/blocks/planks_birch.png"
(HERE / "frame_preview.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}
VENDING = {"up": "#e9ecee", "south": "#d6dadd", "north": "#d6dadd", "east": "#c3c8cc", "west": "#c3c8cc", "down": "#aab0b5"}
VENDING_RED = {"up": "#d2463e", "south": "#c13c35", "north": "#c13c35", "east": "#a8332d", "west": "#a8332d", "down": "#8e2a25"}
PANEL = {"up": "#a9b0b7", "south": "#9aa1a8", "north": "#9aa1a8", "east": "#8a9198", "west": "#8a9198", "down": "#7a8188"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def frame(x, y, z):
    """A frame hanging on the south face of the block at (x, y, z - 16)."""
    return [{"type": "geo", "geo": f"{REL}/frame_preview.geo.json", "texture": f"{REL}/glow_item_frame_v2.png",
             "bones": ["screen"], "position": [x, y, z]},
            {"type": "geo", "geo": f"{REL}/frame_preview.geo.json", "texture": BIRCH_PLANKS,
             "bones": ["border"], "position": [x, y, z]}]


def locker(x, y, z):
    return {"type": "geo", "geo": "/addon/drafts/locker/shulker_preview.geo.json",
            "texture": "/addon/drafts/locker/shulker_white.png", "rotation": [90, 0, 0], "position": [x, y, z]}


def on_wall():
    return [block(-16, 0, 0, WALL), block(0, 0, 0, WALL), block(16, 0, 0, WALL), *frame(0, 0, 16)]


def vending():
    objs = []
    for x, body in ((0, VENDING_RED), (16, VENDING)):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, 16, FLOOR), block(x, 0, 0, body), block(x, 16, 0, body)]
        objs += frame(x, 16, 16)
    return objs


def locker_panel():
    objs = []
    for x in (-24, -8, 8, 24):
        objs.append(block(x, -16, 0, FLOOR))
        for y in (0, 16, 32):
            objs.append(block(x, y, -16, WALL))
            if x == -8 and y == 16:
                objs += [block(x, y, 0, PANEL), *frame(x, y, 16)]
            else:
                objs.append(locker(x, y, 0))
    return objs


def ticket_machines():
    objs = []
    for x in (-16, 0, 16):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, 16, FLOOR), block(x, 0, -16, WALL), block(x, 16, -16, WALL),
                 block(x, 0, 0, PANEL), *frame(x, 0, 16)]
    return objs


sheet = {
    "title": "萬用小螢幕：邊框改成和樺木木框同色（第二版）",
    "columns": 3, "panelWidth": 380, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "正面", "camera": {"azimuth": 0, "elevation": 0, "size": 18, "target": [0, 8, 8]},
         "objects": on_wall()},
        {"label": "斜看：邊框比畫面高出一點點", "camera": {"azimuth": 50, "elevation": 30, "size": 16, "target": [0, 8, 9]},
         "objects": on_wall()},
        {"label": "側面", "camera": {"azimuth": 85, "elevation": 5, "size": 14, "target": [0, 8, 9]},
         "objects": on_wall()},
        {"label": "販賣機", "camera": {"azimuth": 25, "elevation": 12, "size": 54, "target": [8, 14, 6]},
         "objects": vending()},
        {"label": "置物櫃的操作面板", "camera": {"azimuth": 20, "elevation": 12, "size": 80, "target": [0, 22, 0]},
         "objects": locker_panel()},
        {"label": "售票機", "camera": {"azimuth": 25, "elevation": 20, "size": 60, "target": [0, 8, 6]},
         "objects": ticket_machines()},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote glow_item_frame_v2.png, frame_preview.geo.json, preview.json")
