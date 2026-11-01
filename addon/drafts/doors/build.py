"""Build the solid-colour door and trapdoor draft: geometry, textures, preview.

Run from the repository root:
    python3 addon/drafts/doors/build.py

Two colours, light grey and white, share one texture layout. Shapes follow
the vanilla door and trapdoor: 3 pixels thick, a door is two blocks tall.
Vanilla export: spruce door and spruce trapdoor, keeping direction, hinge,
half and open states.

Door bones (each half is its own block, drawn in its own 16-pixel space):
    lower_closed_l, lower_open_l, upper_closed_l, upper_open_l   hinge on the left
    lower_closed_r, lower_open_r, upper_closed_r, upper_open_r   hinge on the right
Closed, the door lies along the north edge with the hinge at the west end
(the _l bones); it opens inward, toward the south. The lever handle is
painted on the texture (decided: no 3D handle), on the end away from the
hinge; faces are mirrored with negative uv sizes so the handle stays on
that end from both sides, open or closed, hinge left or right.

Trapdoor bones: bottom, top, open (standing against the north edge).

Units are texture pixels; a block is 16 x 16 x 16 with x and z in -8..8.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/doors"

COLOURS = {
    "light_gray": {"panel": (192, 196, 199), "border": (168, 173, 177), "edge": (158, 163, 167)},
    "white": {"panel": (238, 239, 239), "border": (214, 217, 219), "edge": (205, 208, 211)},
}
HANDLE = (206, 211, 216)
HANDLE_DARK = (128, 134, 140)

# ---------- texture layout (64 x 32) ----------
# (0, 0)   16x32 door face: upper half rows 0-15, lower half rows 16-31;
#          the handle is near the left edge, which is the free end when the
#          face is seen from the north with the hinge at the west
# (16, 0)  16x16 trapdoor face
# (32, 0)  16x16 edge (one colour, so any strip of it fits)
W, H = 64, 32


def make_texture(c):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(32):
        for x in range(16):
            border = x in (0, 15) or y in (0, 31)
            px[x, y] = c["border"] + (255,) if border else c["panel"] + (255,)
    for y in range(16):
        for x in range(16):
            border = x in (0, 15) or y in (0, 15)
            px[16 + x, y] = c["border"] + (255,) if border else c["panel"] + (255,)
            px[32 + x, y] = c["edge"] + (255,)
    # Lever handle, about level with the top of the lower block:
    # a small plate and a lever pointing toward the hinge.
    for row in (16, 17, 18):
        px[2, row] = HANDLE_DARK + (255,)
    for col in (3, 4, 5):
        px[col, 17] = HANDLE + (255,)
    return img


def face(u, v, w, h):
    return {"uv": [u, v], "uv_size": [w, h]}


def edge(w, h):
    return face(32, 0, w, h)


def flip(f):
    """Mirror a face's texture left to right (a negative uv width)."""
    (u, v), (w, h) = f["uv"], f["uv_size"]
    return {"uv": [u + w, v], "uv_size": [-w, h]}


def door_slab(upper):
    """A closed door half along the north edge."""
    v = 0 if upper else 16
    panel = face(0, v, 16, 16)
    # Seen from the north the free (east) end is on the left, where the
    # texture has its handle; seen from the south it is on the right.
    return {
        "origin": [-8, 0, -8], "size": [16, 16, 3],
        "uv": {"north": panel, "south": flip(panel), "east": edge(3, 16), "west": edge(3, 16),
               "up": edge(16, 3), "down": edge(16, 3)},
    }


SWAP_FACES = {"north": "west", "west": "north", "south": "east", "east": "south", "up": "up", "down": "down"}
MIRROR_FACES = {"east": "west", "west": "east", "north": "north", "south": "south", "up": "up", "down": "down"}


def opened(cube):
    """Swing a closed-door cube open around the hinge at the north-west corner.

    The closed door spans x from the hinge, 3 pixels deep in z; open, it spans
    z from the hinge, 3 pixels deep in x. Swapping the x and z offsets from the
    hinge corner does that; the swap is a reflection, so the textures are
    flipped back to keep the handle on the free end.
    """
    x, y, z = cube["origin"]
    w, h, d = cube["size"]
    return {"origin": [z, y, x], "size": [d, h, w],
            "uv": {SWAP_FACES[k]: flip(v) for k, v in cube["uv"].items()}}


def mirrored(cube):
    """Mirror east-west, to move the hinge to the right."""
    x, y, z = cube["origin"]
    w, h, d = cube["size"]
    return {"origin": [-(x + w), y, z], "size": [w, h, d],
            "uv": {MIRROR_FACES[k]: flip(v) for k, v in cube["uv"].items()}}


def door_bones():
    bones = {}
    for half in ("lower", "upper"):
        closed = [door_slab(half == "upper")]
        bones[f"{half}_closed_l"] = closed
        bones[f"{half}_open_l"] = [opened(c) for c in closed]
        bones[f"{half}_closed_r"] = [mirrored(c) for c in closed]
        bones[f"{half}_open_r"] = [mirrored(opened(c)) for c in closed]
    return bones


def trapdoor_bones():
    flat = {"up": face(16, 0, 16, 16), "down": face(16, 0, 16, 16),
            "north": edge(16, 3), "south": edge(16, 3), "east": edge(16, 3), "west": edge(16, 3)}
    standing = {"north": face(16, 0, 16, 16), "south": face(16, 0, 16, 16),
                "east": edge(3, 16), "west": edge(3, 16), "up": edge(16, 3), "down": edge(16, 3)}
    return {
        "bottom": [{"origin": [-8, 0, -8], "size": [16, 3, 16], "uv": flat}],
        "top": [{"origin": [-8, 13, -8], "size": [16, 3, 16], "uv": flat}],
        "open": [{"origin": [-8, 0, -8], "size": [16, 16, 3], "uv": standing}],
    }


def geometry(identifier, bones):
    return {
        "description": {"identifier": identifier, "texture_width": W, "texture_height": H},
        "bones": [{"name": n, "pivot": [0, 0, 0], "cubes": c} for n, c in bones.items()],
    }


for name, colour in COLOURS.items():
    make_texture(colour).save(HERE / f"door_{name}.png")
geo = {"format_version": "1.12.0", "minecraft:geometry": [
    geometry("geometry.solid_door", door_bones()),
    geometry("geometry.solid_trapdoor", trapdoor_bones()),
]}
(HERE / "doors.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
WALL = {"up": "#e6dfd2", "south": "#d8d0c2", "north": "#d8d0c2", "east": "#c8bfb0", "west": "#c8bfb0", "down": "#b8af9f"}
FLOOR = {"up": "#a7acb0", "south": "#8d9296", "north": "#8d9296", "east": "#7d8286", "west": "#7d8286", "down": "#6d7276"}


def block(x, y, z, color, size=16):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [size, size, size]}


def door(x, z, colour, state="closed", hinge="l", rot=0):
    tex = f"{REL}/door_{colour}.png"
    common = {"type": "geo", "geo": f"{REL}/doors.geo.json", "identifier": "geometry.solid_door",
              "texture": tex, "rotationY": rot}
    return [common | {"bones": [f"lower_{state}_{hinge}"], "position": [x, 0, z]},
            common | {"bones": [f"upper_{state}_{hinge}"], "position": [x, 16, z]}]


def trapdoor(x, y, z, colour, state):
    return {"type": "geo", "geo": f"{REL}/doors.geo.json", "identifier": "geometry.solid_trapdoor",
            "texture": f"{REL}/door_{colour}.png", "bones": [state], "position": [x, y, z]}


def wall_around(xs_door, width_each_side=1):
    """A wall two blocks tall with a lintel, leaving gaps at xs_door."""
    objs = []
    lo, hi = min(xs_door) - 16 * width_each_side, max(xs_door) + 16 * width_each_side
    for x in range(lo, hi + 1, 16):
        for y in (0, 16, 32):
            if x in xs_door and y < 32:
                continue
            objs.append(block(x, y, 0, WALL))
        objs.append(block(x, -16, 0, FLOOR))
    return objs


def floor_row(xs, y=-16):
    return [block(x, y, 0, FLOOR) for x in xs]


cam_door = {"azimuth": 200, "elevation": 18, "size": 64, "target": [0, 22, 0]}
panels = [
    {"label": "淺灰門", "camera": cam_door, "objects": wall_around([0]) + door(0, 0, "light_gray")},
    {"label": "白色門", "camera": cam_door, "objects": wall_around([0]) + door(0, 0, "white")},
    {"label": "淺灰門打開", "camera": {"azimuth": 215, "elevation": 22, "size": 64, "target": [0, 20, 0]},
     "objects": wall_around([0]) + door(0, 0, "light_gray", state="open")},
    {"label": "白色雙開門", "camera": {"azimuth": 200, "elevation": 18, "size": 80, "target": [0, 22, 0]},
     "objects": wall_around([-8, 8]) + door(-8, 0, "white") + door(8, 0, "white", hinge="r")},
]
for colour, label in (("light_gray", "淺灰"), ("white", "白色")):
    panels.append({
        "label": f"{label}地板門：關（下半）、打開",
        "camera": {"azimuth": 30, "elevation": 30, "size": 52, "target": [4, 2, 0]},
        "objects": floor_row([-12, 4, 20]) + [trapdoor(-12, 0, 0, colour, "bottom"), trapdoor(20, 0, 0, colour, "open")],
    })
hatch = []
for x in (-16, 0, 16):
    for z in (-16, 0, 16):
        if (x, z) != (0, 0):
            hatch.append({"type": "block", "color": FLOOR, "origin": [x - 8, -16, z - 8], "size": [16, 16, 16]})
hatch.append(trapdoor(0, -16, 0, "light_gray", "top"))
panels.append({"label": "淺灰地板門嵌在地板上（上半）", "camera": {"azimuth": 30, "elevation": 40, "size": 60, "target": [0, -4, 0]},
               "objects": hatch})
panels.append({"label": "淺灰門從房間內側看", "camera": {"azimuth": 20, "elevation": 14, "size": 40, "target": [0, 16, -4]},
               "objects": wall_around([0]) + door(0, 0, "light_gray")})

sheet = {"title": "單色門與單色地板門（草稿）", "columns": 4, "panelWidth": 330, "panelHeight": 300,
         "background": "#e8edf1", "panels": panels}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote doors.geo.json, door_light_gray.png, door_white.png, preview.json")
