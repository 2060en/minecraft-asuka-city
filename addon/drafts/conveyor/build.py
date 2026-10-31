"""Build the conveyor belt draft: geometry, textures and the preview sheet.

Run from the repository root:
    python3 addon/drafts/conveyor/build.py

A thin belt that sits on top of a block, like the vanilla rail it turns into
in the vanilla export. Three shapes, named after the vanilla rail_direction
values they map to:

    straight   0 (north-south); east-west is the same shape turned 90 degrees
    ascending  4 (rises toward the north); 2, 3, 5 are the same shape turned
    curve      6 (joins the south and east edges); 7, 8, 9 are turned

The powered conveyor (vanilla export: powered rail) uses the straight and
ascending shapes with a texture that differs only slightly; like the powered
rail, it cannot curve.

Units are texture pixels; a block is 16 x 16 x 16 with x and z in -8..8.
The slope is a cube rotated 45 degrees around x. Check the rotation sign in
Blockbench or in the game: the preview tool may not match Bedrock's sign.
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

# ---------- texture layout (64 x 64) ----------
# (0, 0)   16x32 straight belt top, ribs across the belt (long enough for the slope)
# (16, 0)  16x16 curved belt top, ribs radiating from the inner corner
# (16, 16) 16x32 underside
# (32, 0)  32x3  rail side
# (32, 4)  1x3   rail end
# (32, 8)  16x2  belt edge at the open ends
# (32, 16) 32x32 rail top (one colour, so any strip of it fits)
W, H = 64, 64


def make_texture(powered):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(32):
        for x in range(16):
            px[x, y] = BELT_RIB if y % 2 == 0 else BELT
            px[16 + x, 16 + y] = UNDER
    for y in range(16):
        for x in range(16):
            px[16 + x, y] = BELT
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
    for x in range(32):
        for row, color in enumerate(RAIL_ROWS):
            px[32 + x, row] = color
        if powered:
            # The only difference: a yellow line along the rail sides.
            px[32 + x, 1] = POWER_MARK
    for row in range(RAIL_H):
        px[32, 4 + row] = RAIL_CAP
    for x in range(16):
        for row in range(BELT_H):
            px[32 + x, 8 + row] = BELT_EDGE
    for y in range(32):
        for x in range(32):
            px[32 + x, 16 + y] = RAIL_TOP
    return img


def face(u, v, w, h):
    return {"uv": [u, v], "uv_size": [w, h]}


def belt_top(length, width=14):
    return face(1, 0, width, length)


def under(w, d):
    return face(16, 16, w, d)


def rail_side(length):
    return face(32, 0, length, RAIL_H)


def rail_top(w, d):
    return face(32, 16, w, d)


RAIL_END = face(32, 4, 1, RAIL_H)


def belt_end(length):
    return face(32, 8, length, BELT_H)


def r1(x):
    return round(x, 4)


def straight():
    belt = {
        "origin": [-7, 0, -8], "size": [14, BELT_H, 16],
        "uv": {"up": belt_top(16), "down": under(14, 16),
               "north": belt_end(14), "south": belt_end(14)},
    }
    rails = [{
        "origin": [x0, 0, -8], "size": [1, RAIL_H, 16],
        "uv": {"east": rail_side(16), "west": rail_side(16), "up": rail_top(1, 16),
               "down": under(1, 16), "north": RAIL_END, "south": RAIL_END},
    } for x0 in (-8, 7)]
    return [belt] + rails


def ascending():
    """Rises toward the north, from the flat belt height on the south edge
    to the flat belt height of the block above on the north edge.

    The belt's top surface runs from (z = 8, y = 2) to (z = -8, y = 18).
    The cube is 2 pixels longer at the low end, so its lower corner sinks
    into the flat belt next to it and leaves no gap at the joint.
    """
    s = math.sqrt(0.5)
    n = (0.0, s, s)                 # surface normal (up and to the south)
    extra = 2.0                     # extension at the low (south) end
    length = 16 * math.sqrt(2) + extra
    # Midpoint of the top surface, shifted half the extension downhill.
    mid = (0.0, 10.0 - extra / 2 * s, 0.0 + extra / 2 * s)

    def slab(x0, width, height, down_from_top, uv):
        # Centre of a cube whose top is `height - down_from_top` above the belt
        # surface... expressed along the normal from the surface midpoint.
        off = -down_from_top + height / 2
        cx = x0 + width / 2
        cy = mid[1] + n[1] * off
        cz = mid[2] + n[2] * off
        return {
            "origin": [r1(cx - width / 2), r1(cy - height / 2), r1(cz - length / 2)],
            "size": [width, height, r1(length)],
            "pivot": [r1(cx), r1(cy), r1(cz)],
            "rotation": [45, 0, 0],
            "uv": uv,
        }

    belt = slab(-7, 14, BELT_H, BELT_H, {
        "up": belt_top(r1(length)), "down": under(14, r1(length)),
        "north": belt_end(14), "south": belt_end(14),
    })
    rails = [slab(x0, 1, RAIL_H, BELT_H, {
        "east": rail_side(r1(length)), "west": rail_side(r1(length)),
        "up": rail_top(1, r1(length)), "down": under(1, r1(length)),
        "north": RAIL_END, "south": RAIL_END,
    }) for x0 in (-8, 7)]
    return [belt] + rails


def curve():
    """Joins the south and east edges; outer rails on the north and west."""
    belt = {
        "origin": [-7, 0, -7], "size": [15, BELT_H, 15],
        "uv": {"up": face(17, 1, 15, 15), "down": under(15, 15),
               "south": belt_end(15), "east": belt_end(15)},
    }
    north_rail = {
        "origin": [-8, 0, -8], "size": [16, RAIL_H, 1],
        "uv": {"north": rail_side(16), "south": rail_side(16), "up": rail_top(16, 1),
               "down": under(16, 1), "east": RAIL_END, "west": RAIL_END},
    }
    west_rail = {
        "origin": [-8, 0, -7], "size": [1, RAIL_H, 15],
        "uv": {"west": rail_side(15), "east": rail_side(15), "up": rail_top(1, 15),
               "down": under(1, 15), "south": RAIL_END},
    }
    # Where the inner rails of the two neighbouring straights meet.
    inner_post = {
        "origin": [7, BELT_H, 7], "size": [1, RAIL_H - BELT_H, 1],
        "uv": {d: face(32, 4, 1, RAIL_H - BELT_H) for d in ("north", "south", "east", "west")}
              | {"up": rail_top(1, 1)},
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
        geometry("geometry.conveyor_ascending", ascending()),
        geometry("geometry.conveyor_curve", curve()),
    ],
}
(HERE / "conveyor.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
SUPPORT = {"up": "#d4d8db", "south": "#b9bec2", "north": "#b9bec2", "east": "#a3a8ad", "west": "#a3a8ad", "down": "#8d9296"}


def support(x, z, y=0):
    """A support block whose top face is at height y."""
    return {"type": "block", "color": SUPPORT, "position": [x, y, z]}


def piece(kind, x, z, y=0, rot=0, powered=False):
    return {
        "type": "geo", "geo": f"{REL}/conveyor.geo.json",
        "identifier": f"geometry.conveyor_{kind}",
        "texture": f"{REL}/conveyor_powered.png" if powered else f"{REL}/conveyor.png",
        "position": [x, y, z], "rotationY": rot,
    }


def run(pieces, powered=False):
    """pieces: (kind, x, z, y) where y is the height of the block top it sits on.
    The block under an ascending piece also gets the higher block to its north."""
    objs = []
    for kind, x, z, y in pieces:
        objs.append(support(x, z, y))
        objs.append(piece(kind, x, z, y, powered=powered))
    return objs


# An L-shaped run: two straights to the south, the curve, two straights east.
l_run = []
for x, z, kind, rot in [(0, 32, "straight", 0), (0, 16, "straight", 0), (0, 0, "curve", 0),
                        (16, 0, "straight", 90), (32, 0, "straight", 90)]:
    l_run += [support(x, z), piece(kind, x, z, rot=rot)]

# Flat, slope, flat one block higher.
slope = run([("straight", 0, 16, 0), ("ascending", 0, 0, 0), ("straight", 0, -16, 16)])
slope_powered = run([("straight", 0, 16, 0), ("ascending", 0, 0, 0), ("straight", 0, -16, 16)], powered=True)
# Two levels: flat, slope, slope, flat.
climb = run([("straight", 0, 32, 0), ("ascending", 0, 16, 0), ("ascending", 0, 0, 16),
             ("straight", 0, -16, 32)])
# The top straight's support block needs one more block under it.
climb.insert(0, support(0, -16, 16))

sheet = {
    "title": "傳送履帶（草稿）",
    "columns": 3,
    "panelWidth": 380,
    "panelHeight": 320,
    "background": "#e8edf1",
    "panels": [
        {"label": "直線、轉彎、直線", "camera": {"azimuth": 45, "elevation": 40, "size": 78, "target": [12, -6, 12]},
         "objects": l_run},
        {"label": "斜坡：平、上坡、高一層的平", "camera": {"azimuth": 50, "elevation": 28, "size": 64, "target": [0, 4, 0]},
         "objects": slope},
        {"label": "斜坡側面", "camera": {"azimuth": 90, "elevation": 0, "size": 56, "target": [0, 6, 0]},
         "objects": slope},
        {"label": "動力版斜坡", "camera": {"azimuth": 50, "elevation": 28, "size": 64, "target": [0, 4, 0]},
         "objects": slope_powered},
        {"label": "連續爬兩層", "camera": {"azimuth": 55, "elevation": 25, "size": 90, "target": [0, 12, 8]},
         "objects": climb},
        {"label": "斜坡近看（接縫）", "camera": {"azimuth": 60, "elevation": 20, "size": 22, "target": [0, 2, 6]},
         "objects": slope},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote conveyor.geo.json, conveyor.png, conveyor_powered.png, preview.json")
