"""Build the takeaway coffee cup draft: a Bedrock geometry file and its texture.

Run from the repository root:
    python3 addon/drafts/coffee_cup/build.py

Units are texture pixels; a block is 16 x 16 x 16. The block holds 1 to 4 cups
like candles or sea pickles; each count is a bone (count_1 ... count_4) that
the block shows according to its cup-count state.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent

# ---------- texture (16 x 16) ----------
WHITE = (241, 241, 236, 255)
WHITE_LOW = (226, 226, 220, 255)
SLEEVE = (185, 141, 95, 255)
SLEEVE_MARK = (140, 104, 68, 255)
LID = (236, 236, 232, 255)
LID_SIDE = (214, 214, 209, 255)
LID_UNDER = (196, 196, 190, 255)
SIP_HOLE = (58, 58, 58, 255)

tex = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
px = tex.load()

# Cup side, 4 wide x 5 tall at (0, 0): white rim, kraft sleeve, white base.
side_rows = [WHITE, SLEEVE, SLEEVE, SLEEVE, WHITE_LOW]
for y, color in enumerate(side_rows):
    for x in range(4):
        px[x, y] = color
# A small mark on the sleeve, seen in the middle of every side.
px[1, 2] = SLEEVE_MARK
px[2, 2] = SLEEVE_MARK

# Lid side, 5 wide x 1 tall at (0, 5).
for x in range(5):
    px[x, 5] = LID_SIDE

# Lid top, 5 x 5 at (6, 0), with the sip hole near the south edge.
for y in range(5):
    for x in range(5):
        px[6 + x, y] = LID
px[8, 4] = SIP_HOLE  # on the lid rim, in front of the dome

# Lid underside, 5 x 5 at (6, 5); cup bottom, 4 x 4 at (11, 0).
for y in range(5):
    for x in range(5):
        px[6 + x, 5 + y] = LID_UNDER
for y in range(4):
    for x in range(4):
        px[11 + x, y] = WHITE_LOW


def face(u, v, w, h):
    return {"uv": [u, v], "uv_size": [w, h]}


def box(origin, size, uv):
    return {"origin": list(origin), "size": list(size), "uv": uv}


def cup(cx, cz):
    """One cup: a 4 x 5 x 4 body, a 5 x 1 x 5 lid and a low dome on top.

    Square like vanilla sea pickles; cutting the corners at 4 pixels wide
    made the cup read as a cross.
    """
    side = face(0, 0, 4, 5)
    body = box((cx - 2, 0, cz - 2), (4, 5, 4), {
        "north": side, "south": side, "east": side, "west": side,
        "down": face(11, 0, 4, 4),
    })
    lid_side = face(0, 5, 5, 1)
    lid = box((cx - 2.5, 5, cz - 2.5), (5, 1, 5), {
        "north": lid_side, "south": lid_side, "east": lid_side, "west": lid_side,
        "up": face(6, 0, 5, 5), "down": face(6, 5, 5, 5),
    })
    dome_side = face(1, 5, 3, 0.5)
    dome = box((cx - 1.5, 6, cz - 1.5), (3, 0.5, 3), {
        "north": dome_side, "south": dome_side, "east": dome_side, "west": dome_side,
        "up": face(7, 1, 3, 3),
    })
    return [body, lid, dome]


# Cup centres for each count, in pixels from the block centre.
LAYOUTS = {
    1: [(0, 0)],
    2: [(-3, -1), (3, 1)],
    3: [(-3, -2), (3, -2), (0, 3)],
    4: [(-3, -3), (3, -3), (-3, 3), (3, 3)],
}

geometry = {
    "format_version": "1.12.0",
    "minecraft:geometry": [{
        "description": {
            "identifier": "geometry.coffee_cup",
            "texture_width": 16,
            "texture_height": 16,
        },
        "bones": [
            {
                "name": f"count_{n}",
                "pivot": [0, 0, 0],
                "cubes": [c for (x, z) in centres for c in cup(x, z)],
            }
            for n, centres in LAYOUTS.items()
        ],
    }],
}

tex.save(HERE / "coffee_cup.png")
(HERE / "coffee_cup.geo.json").write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")
print("wrote coffee_cup.png and coffee_cup.geo.json")
