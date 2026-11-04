"""Build the tableware draft: white plate, cup and bowl, knife, fork, spoon
and chopsticks, as custom entities (2026-11-03).

Run from the repository root:
    python3 addon/drafts/tableware/build.py
    node tools/preview/render.mjs addon/drafts/tableware/preview.json addon/drafts/tableware/preview.png

Removing the add-on removes them; the author accepts that (2026-11-03).
They work like the vanilla cushion (minecraft:cushion), which the author
uses a lot without lag: no gravity, no AI, no physics, only a small box to
hit. Each is placed by an item; a script puts the entity at the exact point
the player clicked on the top of a block, so it sits on a trapdoor, a slab,
a head or any number of snow layers at the right height, and turns it to the
player's facing in steps of 45 degrees. Hitting one picks it up.

This draft is the look only: one 16 x 16 texture of colour swatches, one
geometry per piece (in pixels, the origin on the surface it stands on), the
and a preview. The item icons are rendered in 3D from these models by
addon/drafts/icons/build.py (v0.7.1; the first ones were drawn flat).
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/tableware"

SWATCHES = {   # name: (u, v, colour), 4 x 4 each
    "white": (0, 0, (246, 246, 246)),
    "white_side": (4, 0, (228, 230, 232)),
    "inner": (8, 0, (214, 216, 218)),
    "shadow": (12, 0, (196, 198, 202)),
    "silver": (0, 4, (210, 214, 218)),
    "silver_side": (4, 4, (168, 173, 178)),
    "wood": (8, 4, (150, 98, 60)),
    "wood_side": (12, 4, (118, 76, 46)),
}


def texture():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for u, v, c in SWATCHES.values():
        d.rectangle((u, v, u + 3, v + 3), fill=c + (255,))
    return img


def sw(name):
    u, v, _ = SWATCHES[name]
    return {"uv": [u, v], "uv_size": [4, 4]}


def box(x, y, z, w, h, d, top="white", side="white_side"):
    """A cube centred on x, z with its bottom at y."""
    faces = {f: sw(side) for f in ("north", "south", "east", "west", "down")}
    faces["up"] = sw(top)
    return {"origin": [x - w / 2, y, z - d / 2], "size": [w, h, d], "uv": faces}


def disc(x, y, z, w, h, top="white", side="white_side"):
    """A rough circle: two crossed boxes, w across."""
    return [box(x, y, z, w, h, w - 2, top, side), box(x, y, z, w - 2, h, w, top, side)]


def octagon(x, y, z, r, h, top="white", side="white_side", lift=0.0):
    """A solid octagonal prism r across the flats from the centre: four bars
    turned 0, 45, 90, 135 degrees fill an octagon exactly."""
    s = 2 * r * math.tan(math.radians(22.5))
    out = []
    for i in range(4):
        c = box(x, y, z, 2 * r, h + i * lift, s, top, side)
        c["pivot"], c["rotation"] = [x, y, z], [0, i * 45, 0]
        out.append(c)
    return out


def ring(x, y, z, r, h, t, top="white", side="white_side"):
    """Eight thin walls round an octagon, t thick: the side of a bowl or a cup."""
    s = 2 * r * math.tan(math.radians(22.5))
    out = []
    for k in range(8):
        c = box(x, y, z + r - t / 2, s + 0.05, h, t, top, side)
        c["pivot"], c["rotation"] = [x, y, z], [0, k * 45, 0]
        out.append(c)
    return out


# Second version (author, 2026-11-04): the plate, bowl and cup looked raised in
# the middle, as a disc lay on top of them. Now each is hollow: a raised rim
# round a lower middle.
PIECES = {
    "plate": octagon(0, 0, 0, 5, 0.35, "inner", "white_side") + ring(0, 0, 0, 5, 0.7, 1.4),
    "bowl": octagon(0, 0, 0, 2, 0.5) + octagon(0, 0.5, 0, 2.6, 0.5, "shadow", "white_side")
            + ring(0, 0.5, 0, 3.4, 2.5, 0.6),
    "cup": octagon(0, 0, 0, 2, 0.8, "shadow", "white_side") + ring(0, 0, 0, 2, 4.5, 0.5)
           + [box(2.6, 1, 0, 1.2, 0.6, 0.8), box(2.6, 3.2, 0, 1.2, 0.6, 0.8), box(3.0, 1, 0, 0.6, 2.8, 0.8)],
    "knife": [box(0, 0, 2, 0.8, 0.5, 3.5, "silver", "silver_side"),
              box(0, 0, -2, 1.1, 0.25, 4.5, "silver", "silver_side")],
    "fork": [box(0, 0, 2, 0.6, 0.3, 4, "silver", "silver_side"), box(0, 0, -0.5, 1.6, 0.3, 1, "silver", "silver_side")]
            + [box(dx, 0, -1.8, 0.35, 0.3, 1.6, "silver", "silver_side") for dx in (-0.6, 0, 0.6)],
    "spoon": [box(0, 0, 2, 0.6, 0.3, 4, "silver", "silver_side"),
              box(0, 0, -1.4, 2, 0.6, 2.6, "silver", "silver_side")],
    "chopsticks": [box(dx, 0, 0, 0.5, 0.5, 9, "wood", "wood_side") for dx in (-0.6, 0.6)],
}
NAMES = {"plate": ("白盤子", "White Plate"), "bowl": ("白碗", "White Bowl"), "cup": ("白杯子", "White Cup"),
         "knife": ("餐刀", "Knife"), "fork": ("叉子", "Fork"), "spoon": ("湯匙", "Spoon"),
         "chopsticks": ("筷子", "Chopsticks")}


texture().save(HERE / "tableware.png")
geos = [{"description": {"identifier": f"geometry.asukatech.{name}", "texture_width": 16, "texture_height": 16},
         "bones": [{"name": name, "pivot": [0, 0, 0], "cubes": cubes}]} for name, cubes in PIECES.items()]
(HERE / "tableware.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos},
                                                    indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
TABLE = {"up": "#c9a27a", "south": "#b38d66", "north": "#b38d66", "east": "#a17d58", "west": "#a17d58", "down": "#8e6c4a"}
STONE = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}
SNOW = {"up": "#f6f8fa", "south": "#e4e8ec", "north": "#e4e8ec", "east": "#d6dbe0", "west": "#d6dbe0", "down": "#c8cdd2"}
HEAD = {"up": "#3a3b3e", "south": "#303134", "north": "#303134", "east": "#2a2b2e", "west": "#2a2b2e", "down": "#222326"}


def piece(name, x, y, z, rot=0):
    return {"type": "geo", "geo": f"{REL}/tableware.geo.json", "identifier": f"geometry.asukatech.{name}",
            "texture": f"{REL}/tableware.png", "position": [x, y, z], "rotationY": rot}


def slab(x, z, h, color):
    return {"type": "block", "color": color, "origin": [x - 8, 0, z - 8], "size": [16, h, 16]}


table = [slab(x, z, 16, TABLE) for x in (-8, 8) for z in (0,)]
setting = [piece("plate", -8, 16, 1), piece("fork", -15, 16, 1), piece("knife", -1.5, 16, 1), piece("spoon", 0.5, 16, 1),
           piece("bowl", 8, 16, 2), piece("chopsticks", 14.5, 16, 2), piece("cup", 6, 16, -5)]
heights = []
for i, (h, color, label) in enumerate(((16, STONE, "full"), (8, STONE, "slab"), (3, TABLE, "trapdoor"),
                                       (6, SNOW, "snow"))):
    x = (i - 1.5) * 18
    heights.append(slab(x, 0, h, color))
    heights.append(piece("plate", x, h, 0))
    heights.append(piece("cup", x + 3, h + 0.5, 2))
heights.append({"type": "block", "color": HEAD, "origin": [41, 0, -4], "size": [8, 8, 8]})
heights.append(piece("cup", 45, 8, 0))
sheet = {
    "title": "餐具（自製實體，草稿）：白盤子、白碗、白杯子、刀叉、湯匙、筷子",
    "columns": 2, "panelWidth": 560, "panelHeight": 340, "background": "#e8edf1",
    "panels": [
        {"label": "一套擺在桌上", "camera": {"azimuth": 20, "elevation": 40, "size": 34, "target": [0, 17, 0]},
         "objects": table + setting},
        {"label": "放在不同高度上：全方塊、半磚、地板門、三層雪、頭顱", "camera": {"azimuth": 20, "elevation": 30, "size": 62, "target": [8, 6, 0]},
         "objects": heights},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

print("wrote tableware.png, tableware.geo.json, preview.json")
