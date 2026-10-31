"""Build the conveyor belt draft: geometry, textures and the preview sheet.

Run from the repository root:
    python3 addon/drafts/conveyor/build.py

A thin belt that sits on top of a block, like the vanilla rail it turns into
in the vanilla export. Straight pieces run north-south; the curve joins the
south and east edges. The powered conveyor (vanilla export: powered rail)
uses the straight shape with a texture that differs only slightly.

Units are texture pixels; a block is 16 x 16 x 16 with x and z in -8..8.
"""
import json
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/conveyor"

BELT_H = 2      # belt thickness
RAIL_H = 3      # side rails stand 1 pixel above the belt

# ---------- colours ----------
BELT = (46, 48, 51, 255)
BELT_RIB = (60, 63, 67, 255)
BELT_EDGE = (34, 35, 37, 255)
UNDER = (70, 72, 75, 255)
RAIL_TOP = (211, 215, 219, 255)
RAIL_ROWS = [(194, 199, 204, 255), (174, 180, 186, 255), (143, 149, 155, 255)]
RAIL_CAP = (154, 160, 166, 255)
POWER_MARK = (227, 181, 40, 255)

# ---------- texture layout (64 x 32) ----------
# (0, 0)   16x16 straight belt top, ribs across the belt
# (16, 0)  16x16 curved belt top, ribs radiating from the inner corner
# (32, 0)  16x3  rail side, (32, 4) 1x3 rail end
# (32, 16) 16x16 rail top (one colour, so any strip of it fits)
# (32, 8)  16x2  belt edge at the open ends
# (48, 0)  16x16 underside
W, H = 64, 32


def make_texture(powered):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            px[x, y] = BELT_RIB if y % 2 == 0 else BELT
            px[16 + x, y] = BELT
            px[48 + x, y] = UNDER
    # Curve: 1-pixel ribs every 12 degrees, drawn as lines from the
    # south-east corner; about 2 pixels apart in the middle of the belt.
    for k in range(8):
        theta = math.radians(6 + 12 * k)
        r = 5.0
        while r < 23:
            x = int(16 - r * math.cos(theta))
            y = int(16 - r * math.sin(theta))
            if 0 <= x < 16 and 0 <= y < 16:
                px[16 + x, y] = BELT_RIB
            r += 0.25
    for x in range(16):
        for row, color in enumerate(RAIL_ROWS):
            px[32 + x, row] = color
        if powered:
            # The only difference: a yellow line along the rail sides.
            px[32 + x, 1] = POWER_MARK
        for row in range(BELT_H):
            px[32 + x, 8 + row] = BELT_EDGE
    for row in range(RAIL_H):
        px[32, 4 + row] = RAIL_CAP
    for y in range(16):
        for x in range(16):
            px[32 + x, 16 + y] = RAIL_TOP
    return img


def face(u, v, w, h):
    return {"uv": [u, v], "uv_size": [w, h]}


RAIL_SIDE = lambda length: face(32, 0, length, RAIL_H)
RAIL_TOP_F = lambda w, d: face(32, 16, w, d)
RAIL_END = face(32, 4, 1, RAIL_H)
BELT_END = lambda length: face(32, 8, length, BELT_H)


def straight():
    belt = {
        "origin": [-7, 0, -8], "size": [14, BELT_H, 16],
        "uv": {"up": face(1, 0, 14, 16), "down": face(49, 0, 14, 16),
               "north": BELT_END(14), "south": BELT_END(14)},
    }
    rails = []
    for x0 in (-8, 7):
        rails.append({
            "origin": [x0, 0, -8], "size": [1, RAIL_H, 16],
            "uv": {"east": RAIL_SIDE(16), "west": RAIL_SIDE(16),
                   "up": RAIL_TOP_F(1, 16),
                   "down": face(48, 0, 1, 16),
                   "north": RAIL_END, "south": RAIL_END},
        })
    return [belt] + rails


def curve():
    """Joins the south and east edges; outer rails on the north and west."""
    belt = {
        "origin": [-7, 0, -7], "size": [15, BELT_H, 15],
        "uv": {"up": face(17, 1, 15, 15), "down": face(49, 1, 15, 15),
               "south": BELT_END(15), "east": BELT_END(15)},
    }
    north_rail = {
        "origin": [-8, 0, -8], "size": [16, RAIL_H, 1],
        "uv": {"north": RAIL_SIDE(16), "south": RAIL_SIDE(16), "up": RAIL_TOP_F(16, 1),
               "down": face(48, 0, 16, 1), "east": RAIL_END, "west": RAIL_END},
    }
    west_rail = {
        "origin": [-8, 0, -7], "size": [1, RAIL_H, 15],
        "uv": {"west": RAIL_SIDE(15), "east": RAIL_SIDE(15), "up": RAIL_TOP_F(1, 15),
               "down": face(48, 0, 1, 15), "south": RAIL_END},
    }
    # Where the inner rails of the two neighbouring straights meet.
    inner_post = {
        "origin": [7, BELT_H, 7], "size": [1, RAIL_H - BELT_H, 1],
        "uv": {d: face(32, 4, 1, RAIL_H - BELT_H) for d in ("north", "south", "east", "west")}
              | {"up": RAIL_TOP_F(1, 1)},
    }
    return [belt, north_rail, west_rail, inner_post]


def geometry(identifier, cubes):
    return {
        "description": {"identifier": identifier, "texture_width": W, "texture_height": H},
        "bones": [{"name": "conveyor", "pivot": [0, 0, 0], "cubes": cubes}],
    }


# ---------- write model and textures ----------
make_texture(False).save(HERE / "conveyor.png")
make_texture(True).save(HERE / "conveyor_powered.png")
geo = {
    "format_version": "1.12.0",
    "minecraft:geometry": [
        geometry("geometry.conveyor_straight", straight()),
        geometry("geometry.conveyor_curve", curve()),
    ],
}
(HERE / "conveyor.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
SUPPORT = {"up": "#d4d8db", "south": "#b9bec2", "north": "#b9bec2", "east": "#a3a8ad", "west": "#a3a8ad", "down": "#8d9296"}


def support(x, z):
    return {"type": "block", "color": SUPPORT, "position": [x, 0, z]}


def piece(kind, x, z, rot=0, powered=False):
    return {
        "type": "geo", "geo": f"{REL}/conveyor.geo.json",
        "identifier": f"geometry.conveyor_{kind}",
        "texture": f"{REL}/conveyor_powered.png" if powered else f"{REL}/conveyor.png",
        "position": [x, 0, z], "rotationY": rot,
    }


# An L-shaped run: two straights to the south, the curve, two straights east.
l_run = []
for x, z, kind, rot in [(0, 32, "straight", 0), (0, 16, "straight", 0), (0, 0, "curve", 0),
                        (16, 0, "straight", 90), (32, 0, "straight", 90)]:
    l_run += [support(x, z), piece(kind, x, z, rot)]

side_by_side = []
for z in (-16, 0, 16):
    side_by_side += [support(-8, z), piece("straight", -8, z),
                     support(24, z), piece("straight", 24, z, powered=True)]

sheet = {
    "title": "傳送履帶（草稿）",
    "columns": 3,
    "panelWidth": 380,
    "panelHeight": 300,
    "background": "#e8edf1",
    "panels": [
        {"label": "直線 1 格", "camera": {"azimuth": 35, "elevation": 30, "size": 34, "target": [0, -2, 0]},
         "objects": [support(0, 0), piece("straight", 0, 0)]},
        {"label": "直線、轉彎、直線", "camera": {"azimuth": 45, "elevation": 40, "size": 78, "target": [12, -6, 12]},
         "objects": l_run},
        {"label": "俯視", "camera": {"azimuth": 0, "elevation": 89, "size": 70, "target": [14, 0, 14]},
         "objects": l_run},
        {"label": "左：一般　右：動力版", "camera": {"azimuth": 30, "elevation": 32, "size": 76, "target": [8, -4, 0]},
         "objects": side_by_side},
        {"label": "一般近看", "camera": {"azimuth": 30, "elevation": 25, "size": 22, "target": [0, 0, 0]},
         "objects": [support(0, 0), piece("straight", 0, 0)]},
        {"label": "動力版近看", "camera": {"azimuth": 30, "elevation": 25, "size": 22, "target": [0, 0, 0]},
         "objects": [support(0, 0), piece("straight", 0, 0, powered=True)]},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote conveyor.geo.json, conveyor.png, conveyor_powered.png, preview.json")
