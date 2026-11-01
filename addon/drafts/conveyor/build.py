"""Build the conveyor draft: geometry, textures and the preview sheet.

Run from the repository root:
    python3 addon/drafts/conveyor/build.py

How the conveyor works (decided 2026-11-01): a real vanilla rail sits on top
of a custom "conveyor body" block. The body is a full block, and its model
also grows up into the rail's space to draw the belt over the rail, so the
rail is hidden but minecarts still ride the real rail. A script copies the
rail's direction and powered state into the body's states; bones below are
shown according to those states. In the vanilla export the body becomes a
vanilla block and the rail stays as it is.

Bones (all in the body's local frame; the block itself is rotated to match
the rail, so only one orientation of each shape is drawn):

    body           the block itself
    belt_straight  over a straight rail (north-south)
    belt_curve     over a curved rail joining the south and east edges
    belt_slope     over a rail rising toward the north, cut off where the
                   model reaches the 30-pixel height limit for block models
    cap_s, cap_n,  the rest of a slope that ends at this block; drawn by
    cap_e          the upper body and reaching into the next block toward
                   the south, north or east

Units are texture pixels; a block is 16 x 16 x 16 with x and z in -8..8.
Slope cubes are rotated 45 degrees; check the rotation sign in Blockbench or
in the game, because the preview tool may not match Bedrock's sign.
"""
import json
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/conveyor"

TOP = 16        # the belt starts on top of the body
BELT_H = 2      # belt thickness
RAIL_H = 3      # side rails stand 1 pixel above the belt
LIMIT = 30      # block models may not reach higher than this
S = math.sqrt(0.5)

# ---------- colours ----------
BELT = (46, 48, 51, 255)
BELT_RIB = (60, 63, 67, 255)
BELT_EDGE = (34, 35, 37, 255)
UNDER = (70, 72, 75, 255)
RAIL_TOP = (211, 215, 219, 255)
RAIL_ROWS = [(194, 199, 204, 255), (174, 180, 186, 255), (143, 149, 155, 255)]
RAIL_CAP = (154, 160, 166, 255)
POWER_OFF = (227, 181, 40, 255)      # the approved yellow line
POWER_ON = (255, 226, 92, 255)       # brighter while the powered rail is on
BODY_LIP = (201, 206, 211, 255)
BODY_EDGE = (126, 132, 138, 255)
BODY = (180, 186, 192, 255)
BODY_SEAM = (160, 166, 172, 255)
BODY_KICK = (110, 116, 122, 255)
BODY_TOP = (191, 197, 202, 255)
BODY_TOP_EDGE = (170, 176, 182, 255)
BODY_BOTTOM = (140, 146, 152, 255)

# ---------- texture layout (64 x 64) ----------
# (0, 0)   16x32 belt, ribs across a belt running north-south
# (16, 0)  16x16 curved belt, ribs radiating from the inner corner
# (16, 16) 16x32 belt underside
# (32, 0)  32x3  rail side;  (32, 4) 1x3 rail end;  (32, 8) 16x2 belt edge
# (32, 16) 32x32 rail top (one colour, so any strip of it fits)
# (0, 32)  16x16 body side;  (0, 48) 16x16 body top;  (16, 48) 16x16 body bottom
# (32, 48) 32x16 belt, ribs across a belt running east-west
W, H = 64, 64


def make_texture(mark):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(32):
        for x in range(16):
            px[x, y] = BELT_RIB if y % 2 == 0 else BELT
            px[16 + x, 16 + y] = UNDER
    for y in range(16):
        for x in range(32):
            px[32 + x, 48 + y] = BELT_RIB if x % 2 == 0 else BELT
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
        if mark:
            px[32 + x, 1] = mark
    for row in range(RAIL_H):
        px[32, 4 + row] = RAIL_CAP
    for x in range(16):
        for row in range(BELT_H):
            px[32 + x, 8 + row] = BELT_EDGE
    for y in range(32):
        for x in range(32):
            px[32 + x, 16 + y] = RAIL_TOP
    # Body: a metal panel with a lip at the top and a kick plate at the bottom.
    for y in range(16):
        for x in range(16):
            if y == 0:
                c = BODY_LIP
            elif y == 1 or y == 14:
                c = BODY_EDGE
            elif y == 15:
                c = BODY_KICK
            else:
                c = BODY_SEAM if x in (0, 15) else BODY
            px[x, 32 + y] = c
            px[x, 48 + y] = BODY_TOP_EDGE if x in (0, 15) or y in (0, 15) else BODY_TOP
            px[16 + x, 48 + y] = BODY_BOTTOM
    return img


def face(u, v, w, h):
    return {"uv": [u, v], "uv_size": [round(w, 4), round(h, 4)]}


def under(w, d):
    return face(16, 16, w, d)


def rail_side(length):
    return face(32, 0, length, RAIL_H)


def rail_top(w, d):
    return face(32, 16, w, d)


RAIL_END = face(32, 4, 1, RAIL_H)


def belt_end(length):
    return face(32, 8, length, BELT_H)


def r4(x):
    return round(x, 4)


def body():
    side = face(0, 32, 16, 16)
    return [{
        "origin": [-8, 0, -8], "size": [16, 16, 16],
        "uv": {"north": side, "south": side, "east": side, "west": side,
               "up": face(0, 48, 16, 16), "down": face(16, 48, 16, 16)},
    }]


def belt_straight():
    belt = {
        "origin": [-7, TOP, -8], "size": [14, BELT_H, 16],
        "uv": {"up": face(1, 0, 14, 16), "down": under(14, 16),
               "north": belt_end(14), "south": belt_end(14)},
    }
    rails = [{
        "origin": [x0, TOP, -8], "size": [1, RAIL_H, 16],
        "uv": {"east": rail_side(16), "west": rail_side(16), "up": rail_top(1, 16),
               "down": under(1, 16), "north": RAIL_END, "south": RAIL_END},
    } for x0 in (-8, 7)]
    return [belt] + rails


def belt_curve():
    """Joins the south and east edges; outer rails on the north and west."""
    belt = {
        "origin": [-7, TOP, -7], "size": [15, BELT_H, 15],
        "uv": {"up": face(17, 1, 15, 15), "down": under(15, 15),
               "south": belt_end(15), "east": belt_end(15)},
    }
    north_rail = {
        "origin": [-8, TOP, -8], "size": [16, RAIL_H, 1],
        "uv": {"north": rail_side(16), "south": rail_side(16), "up": rail_top(16, 1),
               "down": under(16, 1), "east": RAIL_END, "west": RAIL_END},
    }
    west_rail = {
        "origin": [-8, TOP, -7], "size": [1, RAIL_H, 15],
        "uv": {"west": rail_side(15), "east": rail_side(15), "up": rail_top(1, 15),
               "down": under(1, 15), "south": RAIL_END},
    }
    inner_post = {
        "origin": [7, TOP + BELT_H, 7], "size": [1, RAIL_H - BELT_H, 1],
        "uv": {d: face(32, 4, 1, RAIL_H - BELT_H) for d in ("north", "south", "east", "west")}
              | {"up": rail_top(1, 1)},
    }
    return [belt, north_rail, west_rail, inner_post]


def slope(axis, low, high, extend_low=0.0):
    """Belt and rails on a 45-degree slope.

    axis   "z" (belt runs north-south) or "x" (east-west)
    low    (a, y) of the low end of the belt's top surface centre line,
           where a is the z or x coordinate
    high   (a, y) of the high end
    extend_low  how far to extend the cube past the low end, along the slope,
           so it sinks into the flat belt next to it and leaves no gap
    """
    (a0, y0), (a1, y1) = low, high
    da, dy = a1 - a0, y1 - y0
    length = math.hypot(da, dy)
    ua, uy = da / length, dy / length          # unit vector, low to high
    a0, y0 = a0 - ua * extend_low, y0 - uy * extend_low
    length += extend_low
    ma, my = (a0 + a1) / 2, (y0 + y1) / 2      # midpoint of the top surface
    # Top-surface normal: up, leaning away from the high end.
    na = S if ua < 0 else -S
    ny = S
    # Rotation that tilts a cube lying along the axis onto the slope.
    angle = 45 if ua < 0 else -45
    if axis == "x":
        angle = -angle
    rot = [angle, 0, 0] if axis == "z" else [0, 0, angle]

    def cube(across0, width, height, down_from_top, uv):
        off = -down_from_top + height / 2
        ca, cy = ma + na * off, my + ny * off
        cw = across0 + width / 2
        if axis == "z":
            center = [cw, cy, ca]
            size = [width, height, length]
        else:
            center = [ca, cy, cw]
            size = [length, height, width]
        return {
            "origin": [r4(c - s / 2) for c, s in zip(center, size)],
            "size": [r4(s) for s in size],
            "pivot": [r4(c) for c in center],
            "rotation": rot,
            "uv": uv,
        }

    if axis == "z":
        top = face(1, 0, 14, length)
        sides = ("east", "west")
        ends = ("north", "south")
    else:
        top = face(32, 49, length, 14)
        sides = ("north", "south")
        ends = ("east", "west")
    belt = cube(-7, 14, BELT_H, BELT_H, {
        "up": top, "down": under(14, length),
        ends[0]: belt_end(14), ends[1]: belt_end(14),
    })
    rails = [cube(c0, 1, RAIL_H, BELT_H, {
        sides[0]: rail_side(length), sides[1]: rail_side(length),
        "up": rail_top(1, length) if axis == "z" else rail_top(length, 1),
        "down": under(1, length), ends[0]: RAIL_END, ends[1]: RAIL_END,
    }) for c0 in (-8, 7)]
    return [belt] + rails


# The belt surface over a rail rising toward the north starts at the body's
# top + 2 on the south edge and ends 16 higher on the north edge. Rails stand
# 1 above the belt, so the body can only draw the slope up to where the rail
# tops reach the limit; the upper body draws the rest as a cap.
SURF_LOW = TOP + BELT_H                     # 18
CUT = LIMIT - 1 - SURF_LOW                  # rise drawn by the lower body: 11
CUT_A = 8 - CUT                             # z where the lower part ends: -3


def belt_slope():
    return slope("z", (8, SURF_LOW), (CUT_A, SURF_LOW + CUT), extend_low=2)


def cap(side):
    """The upper part of a slope that ends at this block.

    The slope's rail sits one block lower and one block toward `side`. Moved
    into this body's frame (16 over, 16 up), the slope's top surface runs from
    where the lower body stopped drawing to the flat belt on this body.
    """
    lo = (16 + CUT_A, SURF_LOW + CUT - 16)   # (13, 13)
    hi = (8, TOP + BELT_H)                   # (8, 18)
    if side == "s":
        return slope("z", lo, hi)
    if side == "n":
        return slope("z", (-lo[0], lo[1]), (-hi[0], hi[1]))
    if side == "e":
        return slope("x", lo, hi)
    raise ValueError(side)


def bone(name, cubes):
    return {"name": name, "pivot": [0, 0, 0], "cubes": cubes}


# ---------- write model and textures ----------
make_texture(None).save(HERE / "conveyor.png")
make_texture(POWER_OFF).save(HERE / "conveyor_powered.png")
make_texture(POWER_ON).save(HERE / "conveyor_powered_on.png")
for old in ("conveyor.geo.json",):
    (HERE / old).unlink(missing_ok=True)
geo = {
    "format_version": "1.12.0",
    "minecraft:geometry": [{
        "description": {"identifier": "geometry.conveyor_body", "texture_width": W, "texture_height": H},
        "bones": [
            bone("body", body()),
            bone("belt_straight", belt_straight()),
            bone("belt_curve", belt_curve()),
            bone("belt_slope", belt_slope()),
            bone("cap_s", cap("s")),
            bone("cap_n", cap("n")),
            bone("cap_e", cap("e")),
        ],
    }],
}
(HERE / "conveyor_body.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# Sanity check: nothing may reach above the height limit.
for b in geo["minecraft:geometry"][0]["bones"]:
    for c in b["cubes"]:
        if c.get("rotation"):
            continue
        assert c["origin"][1] + c["size"][1] <= LIMIT, b["name"]

# ---------- preview sheet ----------
SUPPORT = {"up": "#d4d8db", "south": "#b9bec2", "north": "#b9bec2", "east": "#a3a8ad", "west": "#a3a8ad", "down": "#8d9296"}


def conveyor(x, z, level=0, bones=("body",), rot=0, tex="conveyor.png"):
    """A conveyor body whose top is at height `level`."""
    return {
        "type": "geo", "geo": f"{REL}/conveyor_body.geo.json", "texture": f"{REL}/{tex}",
        "bones": list(bones), "position": [x, level - 16, z], "rotationY": rot,
    }


def plain(x, z, level=0):
    return {"type": "block", "color": SUPPORT, "position": [x, level, z]}


straight3 = [conveyor(0, z, bones=("body", "belt_straight")) for z in (-16, 0, 16)]

l_run = [conveyor(0, 32, bones=("body", "belt_straight")),
         conveyor(0, 16, bones=("body", "belt_straight")),
         conveyor(0, 0, bones=("body", "belt_curve")),
         conveyor(16, 0, bones=("body", "belt_straight"), rot=90),
         conveyor(32, 0, bones=("body", "belt_straight"), rot=90)]

# Flat, slope rising north, flat one block higher. The upper body draws the
# top of the slope (cap_s); a plain block holds it up.
slope_run = [conveyor(0, 16, bones=("body", "belt_straight")),
             conveyor(0, 0, bones=("body", "belt_slope")),
             conveyor(0, -16, level=16, bones=("body", "belt_straight", "cap_s")),
             plain(0, -16, 0)]

# Two levels: flat, slope, slope, flat.
climb = [conveyor(0, 32, bones=("body", "belt_straight")),
         conveyor(0, 16, bones=("body", "belt_slope")),
         conveyor(0, 0, level=16, bones=("body", "belt_slope", "cap_s")),
         conveyor(0, -16, level=32, bones=("body", "belt_straight", "cap_s")),
         plain(0, 0, 0), plain(0, -16, 16), plain(0, -16, 0)]

powered = ([conveyor(-8, z, bones=("body", "belt_straight"), tex="conveyor_powered.png") for z in (-16, 0, 16)]
           + [conveyor(24, z, bones=("body", "belt_straight"), tex="conveyor_powered_on.png") for z in (-16, 0, 16)])

sheet = {
    "title": "傳送履帶：鐵軌留著，下面墊機身（草稿）",
    "columns": 4,
    "panelWidth": 340,
    "panelHeight": 300,
    "background": "#e8edf1",
    "panels": [
        {"label": "直線 3 格", "camera": {"azimuth": 35, "elevation": 30, "size": 72, "target": [0, -8, 0]},
         "objects": straight3},
        {"label": "直線、轉彎、直線", "camera": {"azimuth": 45, "elevation": 40, "size": 80, "target": [12, -10, 12]},
         "objects": l_run},
        {"label": "沒有鐵軌時，只有機身", "camera": {"azimuth": 35, "elevation": 30, "size": 34, "target": [0, -8, 0]},
         "objects": [conveyor(0, 0)]},
        {"label": "動力版　左：沒通電　右：通電", "camera": {"azimuth": 30, "elevation": 32, "size": 84, "target": [8, -8, 0]},
         "objects": powered},
        {"label": "斜坡：平、上坡、高一層的平", "camera": {"azimuth": 50, "elevation": 28, "size": 72, "target": [0, 0, 0]},
         "objects": slope_run},
        {"label": "斜坡側面", "camera": {"azimuth": 90, "elevation": 0, "size": 64, "target": [0, 2, 0]},
         "objects": slope_run},
        {"label": "連續爬兩層", "camera": {"azimuth": 55, "elevation": 25, "size": 100, "target": [0, 8, 8]},
         "objects": climb},
        {"label": "斜坡上半段的接縫", "camera": {"azimuth": 60, "elevation": 25, "size": 20, "target": [0, 14, -4]},
         "objects": slope_run},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote conveyor_body.geo.json, 3 textures, preview.json")
