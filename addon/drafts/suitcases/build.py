"""Build the suitcase entity drafts: five common suitcases (2026-11-03).

Run from the repository root:
    python3 addon/drafts/suitcases/build.py
    node tools/preview/render.mjs addon/drafts/suitcases/preview.json addon/drafts/suitcases/preview.png

Custom entities, so each has a real cuboid shape (a retextured chest cannot,
it stays 14 x 15 x 14). Designed by Claude (the author asked for five
common ones). Each comes twice (author, 2026-11-03): standing, as a
decoration placed like the tableware, and lying on its back on rails, a
luggage cart that rides the rails like a minecart. Removing the add-on
removes them (accepted).

Sizes follow docs/scale.md, 1 block = 0.75 m, so 1 pixel is about 4.7 cm:

    cabin_navy     20-inch cabin case, navy polycarbonate, vertical ribs   55 x 40 x 23 cm  -> 12 x 8 x 5
    large_red      28-inch check-in case, red, vertical ribs               75 x 50 x 30 cm  -> 16 x 11 x 6
    aluminium      24-inch aluminium case, silver, horizontal ribs         65 x 45 x 26 cm  -> 14 x 10 x 6
    soft_black     24-inch soft-side case, black nylon, front pockets      65 x 45 x 26 cm  -> 14 x 10 x 6
    pink           24-inch hard-shell case, blush pink, horizontal grooves 65 x 45 x 26 cm  -> 14 x 10 x 6

(height x width x depth in pixels, body only; four spinner wheels add 1
below, the retracted handle 1 on top). Each texture is 64 x 32 with the body
on box UVs at (0, 0) and the small parts (wheels, handle) as swatches.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/suitcases"

WHEEL = (34, 35, 38)
HANDLE = (60, 63, 68)
HANDLE_HI = (96, 100, 106)

CASES = {   # name: (zh_TW, en_US, (h, w, d), body colour, style)
    "cabin_navy": ("深藍色登機箱", "Navy Cabin Case", (12, 8, 5), (40, 56, 96), "vertical"),
    "large_red": ("紅色大行李箱", "Red Large Case", (16, 11, 6), (176, 40, 44), "vertical"),
    "aluminium": ("鋁製行李箱", "Aluminium Case", (14, 10, 6), (196, 200, 205), "horizontal"),
    "soft_black": ("黑色布面行李箱", "Black Soft Case", (14, 10, 6), (40, 41, 44), "soft"),
    "pink": ("粉色行李箱", "Pink Case", (14, 10, 6), (230, 178, 178), "grooves"),
}


def shade(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


def face(w, h, colour, style, rng, big):
    """One side of the body, row 0 at the top. `big` is the front or back."""
    f = [[shade(colour, rng.randint(-2, 2)) for _ in range(w)] for _ in range(h)]
    edge = shade(colour, -26 if colour[0] > 80 else 14)
    for y in range(h):
        f[y][0] = f[y][w - 1] = edge
    for x in range(w):
        f[0][x] = f[h - 1][x] = edge
    if style == "vertical" and big:
        for x in range(2, w - 2, 3):
            for y in range(1, h - 1):
                f[y][x] = shade(colour, 22)
                if x + 1 < w - 1:
                    f[y][x + 1] = shade(colour, -14)
    elif style == "horizontal":
        for y in range(2, h - 2, 3):
            for x in range(1, w - 1):
                f[y][x] = shade(colour, 24)
                f[y + 1][x] = shade(colour, -18)
    elif style == "grooves" and big:
        for y in (h // 3, 2 * h // 3):
            for x in range(1, w - 1):
                f[y][x] = shade(colour, -24)
    elif style == "soft":
        for y in range(1, h - 1):            # nylon weave
            for x in range(1, w - 1):
                if (x + y) % 2:
                    f[y][x] = shade(colour, 6)
        if big:                              # two zipped front pockets
            for y in (3, h // 2 + 1):
                for x in range(2, w - 2):
                    f[y][x] = (120, 124, 130)
            f[3][w - 3] = f[h // 2 + 1][w - 3] = (170, 174, 180)   # zip pulls
    if not big:                              # the zip round the case, on the narrow sides
        m = w // 2
        for y in range(1, h - 1):
            f[y][m] = (120, 124, 130) if y % 2 else shade(colour, -30)
    return f


def texture(name):
    _, _, (h, w, d), colour, style = CASES[name]
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    px = img.load()
    rng = random.Random(name)

    def paint(x0, y0, f):
        for y, row in enumerate(f):
            for x, c in enumerate(row):
                px[x0 + x, y0 + y] = c + (255,)
    # box UV at (0, 0): top (d, 0) and bottom (d + w, 0), then east, north, west, south
    paint(d, 0, face(w, d, colour, "plain", rng, False if style != "soft" else False))
    paint(d + w, 0, face(w, d, shade(colour, -20), "plain", rng, False))
    paint(0, d, face(d, h, colour, style, rng, False))
    paint(d, d, face(w, h, colour, style, rng, True))
    paint(d + w, d, face(d, h, colour, style, rng, False))
    paint(2 * d + w, d, face(w, h, colour, style, rng, True))
    for (x, y, c) in ((60, 0, WHEEL), (60, 4, HANDLE), (60, 8, HANDLE_HI)):
        for yy in range(y, y + 4):
            for xx in range(x, x + 4):
                px[xx, yy] = c + (255,)
    return img


def sw(u, v):
    return {"uv": [u, v], "uv_size": [4, 4]}


def box_uv(u, v, w, h, d):
    def f(x, y, a, b):
        return {"uv": [x, y], "uv_size": [a, b]}
    return {"up": f(u + d, v, w, d), "down": f(u + d + w, v, w, d),
            "east": f(u, v + d, d, h), "north": f(u + d, v + d, w, h),
            "west": f(u + d + w, v + d, d, h), "south": f(u + 2 * d + w, v + d, w, h)}


def solid(origin, size, s):
    return {"origin": origin, "size": size, "uv": {f: s for f in ("north", "south", "east", "west", "up", "down")}}


def cubes(name):
    """Standing: wheels at y 0-1, body above, the handle on top; front faces south."""
    _, _, (h, w, d), _, _ = CASES[name]
    x0, z0 = -w / 2, -d / 2
    out = [{"origin": [x0, 1, z0], "size": [w, h, d], "uv": box_uv(0, 0, w, h, d)}]
    for wx in (x0 + 0.25, x0 + w - 1.25):
        for wz in (z0 + 0.25, z0 + d - 1.25):
            out.append(solid([wx, 0, wz], [1, 1, 1], sw(60, 0)))
    hy = 1 + h
    out += [solid([-2.5, hy, z0 + 0.5], [0.8, 1, 0.8], sw(60, 4)),      # the telescopic handle, retracted
            solid([1.7, hy, z0 + 0.5], [0.8, 1, 0.8], sw(60, 4)),
            solid([-2.5, hy + 1, z0 + 0.5], [5, 0.8, 0.8], sw(60, 8))]
    return out


geos = []
for name in CASES:
    geos.append({"description": {"identifier": f"geometry.asukatech.suitcase_{name}", "texture_width": 64, "texture_height": 32},
                 "bones": [{"name": "case", "pivot": [0, 0, 0], "cubes": cubes(name)}]})
    # lying on its back on rails: every cube turned 90 degrees about x round a
    # pivot at the middle of the case, so the case lies with its back 2 pixels
    # above the rail and its middle over the centre of the block
    _, _, (h, w, d), _, _ = CASES[name]
    p, mid = 2 + d / 2, (h + 2) / 2
    lying = [{**c, "origin": [c["origin"][0], c["origin"][1] + p - mid, c["origin"][2]],
              "pivot": [0, p, 0], "rotation": [90, 0, 0]} for c in cubes(name)]
    geos.append({"description": {"identifier": f"geometry.asukatech.luggage_cart_{name}", "texture_width": 64, "texture_height": 32},
                 "bones": [{"name": "case", "pivot": [0, 0, 0], "cubes": lying}]})
def icon(name):
    """16 x 16 item icon: the front of the case, its handle and two wheels."""
    _, _, (h, w, d), _, _ = CASES[name]
    tex = texture(name)
    front = tex.crop((d, d, d + w, d + h))
    scale = 13 / h
    fw, fh = max(1, round(w * scale)), 13
    front = front.resize((fw, fh), Image.NEAREST)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    x0 = (16 - fw) // 2
    img.alpha_composite(front, (x0, 1))
    px = img.load()
    for x in range(x0 + fw // 2 - 2, x0 + fw // 2 + 2):     # the handle
        px[x, 0] = HANDLE_HI + (255,)
    for x in (x0 + 1, x0 + fw - 2):                          # wheels
        px[x, 14] = WHEEL + (255,)
    return img


icons = HERE / "icons"
icons.mkdir(exist_ok=True)
for name in CASES:
    texture(name).save(HERE / f"{name}.png")
    icon(name).save(icons / f"{name}.png")
(HERE / "suitcases.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos},
                                                    indent=1) + "\n", encoding="utf-8")

# ---------- preview sheet ----------
FLOOR = {"up": "#cfc8bb", "south": "#bdb6a9", "north": "#bdb6a9", "east": "#aba497", "west": "#aba497", "down": "#99928a"}
RAIL = {"up": "#8a8f96", "south": "#7a7f86", "north": "#7a7f86", "east": "#6a6f76", "west": "#6a6f76", "down": "#5a5f66"}


def case(name, x, z, rot=0, lying=False):
    ident = f"geometry.asukatech.{'luggage_cart' if lying else 'suitcase'}_{name}"
    return {"type": "geo", "geo": f"{REL}/suitcases.geo.json", "identifier": ident, "texture": f"{REL}/{name}.png",
            "position": [x, 0, z], "rotationY": rot}


def floor(xs, zs, color=FLOOR):
    return [{"type": "block", "color": color, "origin": [x - 8, -16, z - 8], "size": [16, 16, 16]} for x in xs for z in zs]


names = list(CASES)
standing = floor([-32, -16, 0, 16, 32], [0]) + [case(n, (i - 2) * 16, 0) for i, n in enumerate(names)]
backs = floor([-32, -16, 0, 16, 32], [0]) + [case(n, (i - 2) * 16, 0, 180) for i, n in enumerate(names)]
rails = floor([0], [-32, -16, 0, 16, 32], RAIL) + \
    [{"type": "block", "color": "#3a3b3e", "origin": [-6, 0, -40], "size": [12, 0.4, 80]}] + \
    [case(n, 0, (i - 2) * 16, 0, True) for i, n in enumerate(names)]
sheet = {
    "title": "5 種行李箱（自製實體，草稿）：深藍登機箱、紅色大行李箱、鋁製、黑色布面、粉色",
    "columns": 1, "panelWidth": 1000, "panelHeight": 300, "background": "#e8edf1",
    "panels": [
        {"label": "直立（擺飾）：正面", "camera": {"azimuth": 20, "elevation": 15, "size": 46, "target": [0, 9, 0]},
         "objects": standing},
        {"label": "直立：背面與側面", "camera": {"azimuth": 200, "elevation": 15, "size": 46, "target": [0, 9, 0]},
         "objects": backs},
        {"label": "躺著的行李礦車（在鐵軌上）", "camera": {"azimuth": 70, "elevation": 30, "size": 56, "target": [0, 3, 0]},
         "objects": rails},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote 5 textures, suitcases.geo.json, preview.json")
