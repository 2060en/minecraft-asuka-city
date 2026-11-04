"""Build the coffee stand draft: textures that replace the brewing stand.

Run from the repository root:
    python3 addon/drafts/coffee_machine/build.py
    node tools/preview/render.mjs addon/drafts/coffee_machine/preview.json addon/drafts/coffee_machine/preview.png

Resource pack only: brewing_stand.png, brewing_stand_base.png and the item
icon replace the vanilla files, so every brewing stand is a coffee machine.
The vanilla export is simply the brewing stand.

The model is built into the game and cannot change: three small base plates,
a pole in the middle and three arms, each drawn on a flat pane from the pole
out to the edge (vanilla texture, bedrock-samples 2026-11: the pole at
x 7-8, the arms along rows 2-3, the left half with a bottle hanging under the
arm, shown when a bottle is in the stand, the right half without). A boxy
espresso machine is not possible in that shape, so it becomes a pour-over
coffee stand, the kind cafes use: a black steel pole and arms, a white
dripper at the end of each arm, and, when a "bottle" is in, a glass server
of coffee under it. The base plates become a black drip tray.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/coffee_machine"

STEEL = (44, 45, 48)
STEEL_HI = (78, 80, 84)
DRIPPER = (240, 240, 238)
DRIPPER_LO = (206, 206, 204)
FILTER = (226, 214, 190)
GLASS = (186, 208, 218)
GLASS_HI = (232, 242, 246)
COFFEE = (78, 46, 30)
COFFEE_HI = (112, 70, 44)
COLLAR = (150, 104, 66)          # a wooden collar round the server's waist
TRAY = (38, 39, 42)
TRAY_RING = (60, 62, 66)


def put(px, x, y, c):
    px[x, y] = c + (255,)


def stand():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(2, 16):                       # the pole
        put(px, 7, y, STEEL_HI)
        put(px, 8, y, STEEL)
    for x in range(2, 14):                       # the arms
        put(px, x, 2, STEEL_HI)
        put(px, x, 3, STEEL)
    for x0 in (1, 11):                           # a dripper at the end of each arm
        for x in range(x0, x0 + 4):
            put(px, x, 4, DRIPPER)
        for x in range(x0, x0 + 4):
            put(px, x, 5, DRIPPER if x < x0 + 3 else DRIPPER_LO)
        put(px, x0 + 1, 6, DRIPPER)
        put(px, x0 + 2, 6, DRIPPER_LO)
        put(px, x0 + 1, 4, FILTER)               # the paper filter showing at the top
        put(px, x0 + 2, 4, FILTER)
    # the left half is drawn when a bottle is in: a glass server of coffee
    for y in range(8, 15):
        for x in range(0, 5):
            put(px, x, y, GLASS)
    put(px, 0, 8, GLASS_HI)
    put(px, 4, 8, GLASS_HI)
    for x in range(1, 4):
        put(px, x, 7, GLASS)                     # the neck
    for x in range(0, 5):
        put(px, x, 10, COLLAR)
    for y in range(11, 15):
        for x in range(0, 5):
            put(px, x, y, COFFEE)
    put(px, 1, 11, COFFEE_HI)
    put(px, 5, 9, GLASS)                         # the handle
    put(px, 5, 10, GLASS)
    put(px, 5, 11, GLASS)
    return img


def base():
    """The drip tray: black, with a faint ring where each of the three base
    plates sits (the plates' tops use these circles)."""
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    rng = random.Random(3)
    for y in range(16):
        for x in range(16):
            d = rng.randint(-2, 2)
            put(px, x, y, tuple(v + d for v in TRAY))
    for cx, cy in ((3.5, 4.5), (11.5, 7.5), (3.5, 11.5)):
        for y in range(16):
            for x in range(16):
                if abs(math.hypot(x - cx, y - cy) - 2.2) < 0.5:
                    put(px, x, y, TRAY_RING)
    return img


def icon():
    """The item icon: the stand itself, laid out like the vanilla icon (pole,
    a crossbar, a dripper hanging at each end, the tray under it). The first
    icon was the glass server; the author wanted the stand (2026-11-04)."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for x in range(3, 13):                       # the tray
        put(px, x, 13, TRAY_RING)
        put(px, x, 14, TRAY)
    for y in range(3, 13):                       # the pole
        put(px, 7, y, STEEL_HI)
        put(px, 8, y, STEEL)
    put(px, 7, 2, STEEL_HI)
    put(px, 8, 2, STEEL_HI)
    for x in range(1, 15):                       # the crossbar
        put(px, x, 4, STEEL_HI)
        put(px, x, 5, STEEL)
    for x0 in (1, 10):                           # a white cone dripper under each end
        for x in range(x0, x0 + 5):
            put(px, x, 6, DRIPPER)
        for x in range(x0 + 1, x0 + 4):
            put(px, x, 6, FILTER)                # the paper filter inside
        for x in range(x0, x0 + 5):
            put(px, x, 7, DRIPPER if x < x0 + 4 else DRIPPER_LO)
        for x in range(x0 + 1, x0 + 4):
            put(px, x, 8, DRIPPER if x < x0 + 3 else DRIPPER_LO)
        put(px, x0 + 2, 9, DRIPPER_LO)
    for y in range(1, 16):                       # outline
        for x in range(0, 16):
            if px[x, y][3] == 0 and any(px[x + dx, y + dy][3] and px[x + dx, y + dy][:3] != (90, 92, 96)
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                        if 0 <= x + dx < 16 and 0 <= y + dy < 16):
                put(px, x, y, (90, 92, 96))
    return img


stand().save(HERE / "brewing_stand.png")
base().save(HERE / "brewing_stand_base.png")
icon().save(HERE / "brewing_stand_item.png")

# Preview model, after Java Edition's brewing stand: the pole, three base
# plates, three panes (two empty arms and one with a server).
def pane(angle, bottle):
    uv = {"uv": [8, 0], "uv_size": [-8, 16]} if bottle else {"uv": [8, 0], "uv_size": [8, 16]}
    return {"origin": [0, 0, 0], "size": [8, 16, 0], "pivot": [0, 0, 0], "rotation": [0, angle, 0],
            "uv": {"south": uv, "north": uv}}


def plate(x, z):
    face = {"uv": [x + 8, z + 8], "uv_size": [6, 6]}
    side = {"uv": [0, 0], "uv_size": [6, 2]}
    return {"origin": [x, 0, z], "size": [6, 2, 6], "uv": {"up": face, "north": side, "south": side,
                                                           "east": side, "west": side}}


geo = {"format_version": "1.12.0", "minecraft:geometry": [
    {"description": {"identifier": "geometry.stand_preview", "texture_width": 16, "texture_height": 16},
     "bones": [{"name": "stand", "pivot": [0, 0, 0], "cubes": [
         {"origin": [-1, 0, -1], "size": [2, 14, 2], "uv": {f: {"uv": [7, 2], "uv_size": [2, 14]}
                                                             for f in ("north", "south", "east", "west")}},
         pane(0, False), pane(135, False), pane(-135, True)]}]},
    {"description": {"identifier": "geometry.base_preview", "texture_width": 16, "texture_height": 16},
     "bones": [{"name": "base", "pivot": [0, 0, 0], "cubes": [plate(1, -3), plate(-6, -7), plate(-6, 1)]}]},
]}
(HERE / "stand_preview.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

COUNTER = {"up": "#e9e4da", "south": "#d6d0c4", "north": "#d6d0c4", "east": "#c4beb2", "west": "#c4beb2", "down": "#b0aa9e"}


def machine(x):
    return [{"type": "block", "color": COUNTER, "origin": [x - 8, -16, -8], "size": [16, 16, 16]},
            {"type": "geo", "geo": f"{REL}/stand_preview.geo.json", "identifier": "geometry.base_preview",
             "texture": f"{REL}/brewing_stand_base.png", "position": [x, 0, 0]},
            {"type": "geo", "geo": f"{REL}/stand_preview.geo.json", "identifier": "geometry.stand_preview",
             "texture": f"{REL}/brewing_stand.png", "position": [x, 0, 0]}]


sheet = {
    "title": "咖啡機：釀造台換材質，形狀固定，所以做成手沖咖啡架（草稿，形狀照 Java 版推測）",
    "columns": 2, "panelWidth": 520, "panelHeight": 340, "background": "#e8edf1",
    "panels": [
        {"label": "斜看：黑色支架、白色濾杯，放了「瓶子」的那一邊有咖啡壺", "camera": {"azimuth": 30, "elevation": 22, "size": 26, "target": [0, 7, 0]},
         "objects": machine(0)},
        {"label": "吧台上一排", "camera": {"azimuth": 20, "elevation": 20, "size": 60, "target": [0, 6, 0]},
         "objects": machine(-18) + machine(0) + machine(18)},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote brewing_stand.png, brewing_stand_base.png, brewing_stand_item.png, preview.json")
