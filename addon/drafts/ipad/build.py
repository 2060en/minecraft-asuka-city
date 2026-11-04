"""Build the iPad draft: a custom entity lying flat, placed like the tableware.

Run from the repository root:
    python3 addon/drafts/ipad/build.py
    node tools/preview/render.mjs addon/drafts/ipad/preview.json addon/drafts/ipad/preview.png

Removing the add-on removes it (accepted by the author, 2026-11-03). It is
placed with an item at the clicked point on top of a block, like the
tableware (addon/pack/behavior/scripts/main.js), and a hit picks it up.

Size: 10 x 7 pixels and 0.4 thick, about twice the real iPad (25 x 18 cm),
like the other small props, so the screen can be seen. The entity texture is
64 x 64, so the small faces still carry detail: the screen (a home screen
with app icons and a dock) on the top, the aluminium back with the same
small apple logo as the laptop paintings on the bottom.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/ipad"

BEZEL = (18, 18, 20)
ALU = (196, 200, 205)
ALU_EDGE = (168, 172, 178)
LOGO = (246, 247, 248)
ICON_COLOURS = [(240, 80, 70), (250, 190, 60), (90, 200, 110), (70, 150, 240), (170, 110, 230),
                (250, 250, 250), (60, 60, 64), (240, 130, 180), (80, 210, 220), (250, 150, 60)]

W, H = 40, 28          # the screen and the back, in texture pixels


def put(px, x, y, c):
    px[x, y] = c + (255,)


def screen(px, x0, y0):
    rng = random.Random(4)
    for y in range(H):
        for x in range(W):
            t = (x + y) / (W + H)               # wallpaper: blue to violet
            c = (int(40 + 90 * t), int(90 - 30 * t), int(190 - 20 * t))
            put(px, x0 + x, y0 + y, c)
    for x in range(W):                          # bezel
        for y in (0, 1, H - 2, H - 1):
            put(px, x0 + x, y0 + y, BEZEL)
    for y in range(H):
        for x in (0, 1, W - 2, W - 1):
            put(px, x0 + x, y0 + y, BEZEL)
    for x in range(4, 9):                       # status bar: the time
        put(px, x0 + x, y0 + 3, (240, 240, 244))
    for row in range(3):                        # app icons: 3 rows of 6
        for col in range(6):
            c = rng.choice(ICON_COLOURS)
            ix, iy = x0 + 5 + col * 5, y0 + 6 + row * 5
            for y in range(3):
                for x in range(3):
                    put(px, ix + x, iy + y, c)
    for x in range(8, W - 8):                   # the dock
        for y in range(H - 7, H - 3):
            put(px, x0 + x, y0 + y, (150, 160, 200))
    for i in range(4):
        c = ICON_COLOURS[i * 2]
        ix = x0 + 11 + i * 5
        for y in range(H - 6, H - 4):
            for x in range(3):
                put(px, ix + x, y0 + y, c)


def back(px, x0, y0):
    rng = random.Random(5)
    for y in range(H):
        for x in range(W):
            put(px, x0 + x, y0 + y, tuple(v + rng.randint(-2, 2) for v in ALU))
    for x in range(W):
        put(px, x0 + x, y0, ALU_EDGE)
        put(px, x0 + x, y0 + H - 1, ALU_EDGE)
    for y in range(H):
        put(px, x0, y0 + y, ALU_EDGE)
        put(px, x0 + W - 1, y0 + y, ALU_EDGE)
    cx, cy = x0 + W // 2 - 2, y0 + H // 2 - 2   # the apple: a small round shape and a leaf
    for y in range(4):
        for x in range(4):
            if (x, y) not in ((0, 0), (3, 0), (0, 3), (3, 3)):
                put(px, cx + x, cy + y, LOGO)
    put(px, cx + 2, cy - 1, LOGO)
    for x in range(3, 6):                       # the camera
        for y in range(3, 6):
            put(px, x0 + x, y0 + y, (40, 40, 44))


def texture():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    px = img.load()
    screen(px, 0, 0)
    back(px, 0, 32)
    for y in range(60, 64):                     # the edge
        for x in range(60, 64):
            put(px, x, y, ALU_EDGE)
    return img


edge = {"uv": [60, 60], "uv_size": [4, 4]}
cube = {"origin": [-5, 0, -3.5], "size": [10, 0.4, 7],
        "uv": {"up": {"uv": [0, 0], "uv_size": [W, H]}, "down": {"uv": [0, 32], "uv_size": [W, H]},
               "north": edge, "south": edge, "east": edge, "west": edge}}
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.asukatech.ipad", "texture_width": 64, "texture_height": 64},
    "bones": [{"name": "ipad", "pivot": [0, 0, 0], "cubes": [cube]}]}]}
texture().save(HERE / "ipad.png")
(HERE / "ipad.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# the item icon: the screen, drawn small
icon = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
small = texture().crop((0, 0, W, H)).resize((14, 10), Image.NEAREST)
icon.alpha_composite(small, (1, 3))
icon.save(HERE / "ipad_item.png")

TABLE = {"up": "#e9e4da", "south": "#d6d0c4", "north": "#d6d0c4", "east": "#c4beb2", "west": "#c4beb2", "down": "#b0aa9e"}


def ipad(x, z, rot=0, flip=False):
    obj = {"type": "geo", "geo": f"{REL}/ipad.geo.json", "texture": f"{REL}/ipad.png", "position": [x, 16, z],
           "rotationY": rot}
    if flip:
        obj["rotation"] = [180, 0, 0]
        obj["pivot"] = [0, 0.2, 0]
    return obj


table = [{"type": "block", "color": TABLE, "origin": [x - 8, 0, -8], "size": [16, 16, 16]} for x in (-8, 8)]
sheet = {"title": "iPad（自製實體，草稿）：平放在桌上，約實物的兩倍大",
         "columns": 2, "panelWidth": 520, "panelHeight": 320, "background": "#e8edf1",
         "panels": [
             {"label": "螢幕朝上", "camera": {"azimuth": 15, "elevation": 55, "size": 22, "target": [-8, 16, 0]},
              "objects": table + [ipad(-8, 0)]},
             {"label": "背面（翻過來看）", "camera": {"azimuth": 15, "elevation": 55, "size": 22, "target": [8, 16, 0]},
              "objects": table + [ipad(8, 0, flip=True)]},
         ]}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote ipad.png, ipad.geo.json, ipad_item.png, preview.json")
