"""Build the screen block draft: a custom block with a black edge that glows.

Run from the repository root:
    python3 addon/drafts/screen_block/build.py

Decided by the author 2026-11-03: the retextured glow item frame always
keeps the game's birch border, which does not suit a screen, so the screen
becomes its own block, `asukatech:screen`: a thin panel with a black edge
and the standby picture of the first screen draft (addon/drafts/screen/
glow_item_frame.png), lit by itself. It can hang on a wall or lie on a floor
or ceiling, like an item frame. In the vanilla version it becomes an empty
glow item frame facing the same way (addon/mapping.json).

The panel is 14 x 14 pixels and 1 pixel thick, against the face of the block
it was placed on; its front shows the middle 14 x 14 of the texture, so a
1-pixel black edge round a 12 x 12 picture. The sides and back are black.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/screen_block"
TEXTURE = "/addon/drafts/screen/glow_item_frame.png"

black = {"uv": [0, 0], "uv_size": [1, 1]}
panel = {"origin": [-7, 1, -8], "size": [14, 14, 1],
         "uv": {"south": {"uv": [1, 1], "uv_size": [14, 14]}, "north": black,
                "east": black, "west": black, "up": black, "down": black}}
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.asukatech.screen", "texture_width": 16, "texture_height": 16},
    "bones": [{"name": "screen", "pivot": [0, 0, 0], "cubes": [panel]}],
}]}
(HERE / "screen.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}
VENDING = {"up": "#e9ecee", "south": "#d6dadd", "north": "#d6dadd", "east": "#c3c8cc", "west": "#c3c8cc", "down": "#aab0b5"}
VENDING_RED = {"up": "#d2463e", "south": "#c13c35", "north": "#c13c35", "east": "#a8332d", "west": "#a8332d", "down": "#8e2a25"}
PANEL = {"up": "#a9b0b7", "south": "#9aa1a8", "north": "#9aa1a8", "east": "#8a9198", "west": "#8a9198", "down": "#7a8188"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def screen(x, y, z):
    """On the south face of the block at (x, y, z - 16)."""
    return {"type": "geo", "geo": f"{REL}/screen.geo.json", "texture": TEXTURE, "position": [x, y, z]}


def vending():
    objs = []
    for x, body in ((0, VENDING_RED), (16, VENDING)):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, 16, FLOOR), block(x, 0, 0, body), block(x, 16, 0, body),
                 screen(x, 16, 16)]
    return objs


def ticket_machines():
    objs = []
    for x in (-16, 0, 16):
        objs += [block(x, -16, 0, FLOOR), block(x, -16, 16, FLOOR), block(x, 0, -16, WALL), block(x, 16, -16, WALL),
                 block(x, 0, 0, PANEL), screen(x, 0, 16)]
    return objs


on_wall = [block(-16, 0, 0, WALL), block(0, 0, 0, WALL), block(16, 0, 0, WALL), screen(0, 0, 16)]
sheet = {
    "title": "小螢幕方塊（自製，會發光；原味版是發光物品框架）",
    "columns": 3, "panelWidth": 380, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "正面：1 像素黑邊", "camera": {"azimuth": 0, "elevation": 0, "size": 18, "target": [0, 8, 8]},
         "objects": on_wall},
        {"label": "販賣機", "camera": {"azimuth": 25, "elevation": 12, "size": 54, "target": [8, 14, 6]},
         "objects": vending()},
        {"label": "售票機", "camera": {"azimuth": 25, "elevation": 20, "size": 60, "target": [0, 8, 6]},
         "objects": ticket_machines()},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote screen.geo.json, preview.json")
