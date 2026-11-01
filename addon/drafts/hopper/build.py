"""Build the grey-white hopper: three textures that replace the hopper's.

Run from the repository root:
    python3 addon/drafts/hopper/build.py

Resource pack only (decided: no custom urinal block). The files replace
textures/blocks/hopper_outside.png, hopper_top.png and hopper_inside.png, so
every hopper is grey-white porcelain; one hung on a wall with its spout in the
wall reads as a urinal. The vanilla export is simply the hopper.

The hopper model is built into the game. Like the vanilla textures, the
outside texture is read by height: rows 0-5 are the bowl's outer walls,
rows 5-6 the bowl's floor edge, rows 6-11 the middle section and rows 12-15
the spout. The preview model below follows that layout.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/hopper"

PORCELAIN = (230, 232, 233)
PORCELAIN_HI = (242, 243, 244)
PORCELAIN_LO = (210, 213, 215)
MIDDLE = (222, 224, 226)
PIPE = (176, 181, 186)
PIPE_LO = (150, 155, 160)
RIM = (240, 241, 242)
RIM_INNER = (218, 220, 222)
BOWL = (214, 217, 219)
BOWL_DEEP = (190, 194, 198)
DRAIN = (120, 125, 130)


def jitter(c, rng, amount=2, extra=0):
    return tuple(max(0, min(255, v + rng.randint(-amount, amount) + extra)) for v in c) + (255,)


def streaks(seed, count=7):
    """A few short horizontal streaks, the same faint grain as the doors."""
    rng = random.Random(seed)
    out = {}
    for _ in range(count):
        y, x0 = rng.randrange(16), rng.randrange(14)
        shade = rng.choice((-4, -3, 3, 4))
        for x in range(x0, min(16, x0 + rng.randint(3, 5))):
            out[(x, y)] = shade
    return out


def outside():
    rng = random.Random(3)
    grain = streaks(4)
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            if y == 0:
                c = PORCELAIN_HI
            elif y < 5:
                c = PORCELAIN
            elif y == 5:
                c = PORCELAIN_LO
            elif y < 12:
                c = MIDDLE if y < 11 else PORCELAIN_LO
            else:
                c = PIPE if y < 15 else PIPE_LO
            px[x, y] = jitter(c, rng, extra=grain.get((x, y), 0))
    return img


def top():
    rng = random.Random(5)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            ring = min(x, y, 15 - x, 15 - y)
            if ring == 0:
                px[x, y] = jitter(RIM, rng)
            elif ring == 1:
                px[x, y] = jitter(RIM_INNER, rng)
            # The middle stays transparent: it is the bowl's opening.
    return img


def inside():
    rng = random.Random(6)
    grain = streaks(7)
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            d = max(abs(x - 7.5), abs(y - 7.5))
            if d < 1.5:
                c = DRAIN
            elif d < 4.5:
                c = BOWL_DEEP
            else:
                c = BOWL
            px[x, y] = c + (255,) if c == DRAIN else jitter(c, rng, extra=grain.get((x, y), 0))
    return img


textures = {"hopper_outside": outside(), "hopper_top": top(), "hopper_inside": inside()}
for name, img in textures.items():
    img.save(HERE / f"{name}.png")
# One atlas for the preview tool, which takes one texture per model.
atlas = Image.new("RGBA", (48, 16), (0, 0, 0, 0))
for i, name in enumerate(textures):
    atlas.paste(textures[name], (16 * i, 0))
atlas.save(HERE / "preview_atlas.png")

# ---------- preview model ----------
OFF = {"outside": 0, "top": 16, "inside": 32}


def element(x1, y1, z1, x2, y2, z2, faces):
    """A cube in 0-16 block coordinates with UVs read from its position,
    the way block models do; faces maps face name to texture name."""
    uv = {}
    rect = {
        "north": (16 - x2, 16 - y2, x2 - x1, y2 - y1),
        "south": (x1, 16 - y2, x2 - x1, y2 - y1),
        "west": (z1, 16 - y2, z2 - z1, y2 - y1),
        "east": (16 - z2, 16 - y2, z2 - z1, y2 - y1),
        "up": (x1, z1, x2 - x1, z2 - z1),
        "down": (x1, 16 - z2, x2 - x1, z2 - z1),
    }
    for f, tex in faces.items():
        u, v, w, h = rect[f]
        uv[f] = {"uv": [u + OFF[tex], v], "uv_size": [w, h]}
    return {"origin": [x1 - 8, y1, z1 - 8], "size": [x2 - x1, y2 - y1, z2 - z1], "uv": uv}


O, T, I = "outside", "top", "inside"
bowl = [
    element(0, 10, 0, 16, 11, 16, {"north": O, "south": O, "east": O, "west": O, "up": I, "down": O}),
    element(0, 11, 0, 16, 16, 2, {"north": O, "south": I, "east": O, "west": O, "up": T}),
    element(0, 11, 14, 16, 16, 16, {"south": O, "north": I, "east": O, "west": O, "up": T}),
    element(0, 11, 2, 2, 16, 14, {"west": O, "east": I, "up": T}),
    element(14, 11, 2, 16, 16, 14, {"east": O, "west": I, "up": T}),
    element(4, 4, 4, 12, 10, 12, {"north": O, "south": O, "east": O, "west": O, "down": O}),
]
spout_down = [element(6, 0, 6, 10, 4, 10, {"north": O, "south": O, "east": O, "west": O, "down": O})]
spout_north = [element(6, 4, 0, 10, 8, 4, {"north": O, "south": O, "east": O, "west": O, "up": O, "down": O})]
geo = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.hopper_preview", "texture_width": 48, "texture_height": 16},
    "bones": [
        {"name": "bowl", "pivot": [0, 0, 0], "cubes": bowl},
        {"name": "spout_down", "pivot": [0, 0, 0], "cubes": spout_down},
        {"name": "spout_north", "pivot": [0, 0, 0], "cubes": spout_north},
    ],
}]}
(HERE / "hopper_preview.geo.json").write_text(json.dumps(geo, indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
TILE = {"up": "#cfdbe3", "south": "#bccbd5", "north": "#bccbd5", "east": "#aebdc7", "west": "#aebdc7", "down": "#9fb0bb"}
FLOOR = {"up": "#9ea4a9", "south": "#858b90", "north": "#858b90", "east": "#767c81", "west": "#767c81", "down": "#666c71"}


def block(x, y, z, color):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": [16, 16, 16]}


def hopper(x, y, z, spout="down", rot=0):
    return {"type": "geo", "geo": f"{REL}/hopper_preview.geo.json", "texture": f"{REL}/preview_atlas.png",
            "bones": ["bowl", f"spout_{spout}"], "position": [x, y, z], "rotationY": rot}


restroom = []
for x in range(-32, 33, 16):
    for y in (0, 16, 32):
        restroom.append(block(x, y, -16, TILE))
    restroom.append(block(x, -16, 0, FLOOR))
    restroom.append(block(x, -16, -16, FLOOR))
for x in (-16, 0, 16):
    restroom.append(hopper(x, 0, 0, spout="north"))

single = [block(0, -16, 0, FLOOR), hopper(0, 0, 0)]
one_urinal = [block(x, y, -16, TILE) for x in (-16, 0, 16) for y in (0, 16)] + [block(0, -16, 0, FLOOR), hopper(0, 0, 0, spout="north")]

sheet = {
    "title": "漏斗：灰白色（草稿）",
    "columns": 3, "panelWidth": 380, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "平常放在地上", "camera": {"azimuth": 35, "elevation": 30, "size": 30, "target": [0, 6, 0]},
         "objects": single},
        {"label": "接在牆上當小便斗", "camera": {"azimuth": 35, "elevation": 20, "size": 40, "target": [0, 6, -2]},
         "objects": one_urinal},
        {"label": "往下看進去", "camera": {"azimuth": 20, "elevation": 65, "size": 26, "target": [0, 8, 0]},
         "objects": one_urinal},
        {"label": "廁所：三個小便斗並排", "camera": {"azimuth": 25, "elevation": 18, "size": 90, "target": [0, 10, -4]},
         "objects": restroom},
        {"label": "側面", "camera": {"azimuth": 90, "elevation": 10, "size": 40, "target": [0, 6, -2]},
         "objects": one_urinal},
        {"label": "正面", "camera": {"azimuth": 0, "elevation": 8, "size": 40, "target": [0, 6, -2]},
         "objects": one_urinal},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote hopper_outside.png, hopper_top.png, hopper_inside.png, preview files")
