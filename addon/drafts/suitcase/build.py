"""Build the suitcase draft: textures that replace the chest.

Run from the repository root:
    python3 addon/drafts/suitcase/build.py

Resource pack only: chest.png replaces textures/entity/chest/normal.png and
chest_double.png replaces double_normal.png, so every chest (the author has
few that matter, 2026-11-03) looks like a black hard-shell suitcase standing
upright, and a double chest like two of them side by side. The trapped chest
and the ender chest keep their own textures. The vanilla export is simply
the chest.

The vanilla chest model is a 14 x 10 x 14 base under a 14 x 5 x 14 lid,
plus a 2 x 4 x 1 latch on the front, all on box UVs: lid at (0, 0), base at
(0, 19), latch at (0, 0) (bedrock-samples, 2026-11). The double chest is the
same with a width of 30. The front and back become the ribbed shell, the
two narrow sides the zip running round the middle, the latch a small lock
badge; the lid top carries the handle.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/suitcase"

SHELL = (36, 37, 40)
SHELL_HI = (54, 56, 60)          # the raised ribs
SHELL_LO = (26, 27, 29)          # the grooves beside them
EDGE = (22, 22, 24)
ZIP = (78, 80, 84)
ZIP_TAPE = (30, 31, 33)
WHEEL = (18, 18, 19)
HUB = (96, 98, 102)
HANDLE = (88, 90, 94)
HANDLE_DARK = (58, 60, 64)
BADGE = (150, 154, 158)
INSIDE = (30, 30, 32)


def noise(c, rng):
    d = rng.randint(-2, 2)
    return tuple(max(0, min(255, v + d)) for v in c)


def front(w, h, rng, lid):
    """The ribbed shell of the front or back, row 0 at the top. `lid` is the
    top 5 rows of the 15, the rest the base; ribs run the whole height."""
    f = [[noise(SHELL, rng) for _ in range(w)] for _ in range(h)]
    panels = [(0, w)] if w < 20 else [(0, w // 2 - 1), (w // 2 + 1, w)]
    for a, b in panels:
        for x in range(a, b):
            for y in range(h):
                if x in (a, b - 1):
                    f[y][x] = EDGE
                elif (x - a) % 4 == 2:
                    f[y][x] = noise(SHELL_HI, rng)
                elif (x - a) % 4 == 3:
                    f[y][x] = noise(SHELL_LO, rng)
        if not lid:                          # wheels at the two bottom corners
            for x in (a + 1, b - 2):
                f[h - 1][x] = WHEEL
                f[h - 2][x] = WHEEL
                f[h - 1][x + (1 if x == a + 1 else -1)] = HUB
    if w >= 20:                              # the gap between the two cases
        for x in (w // 2 - 1, w // 2):
            for y in range(h):
                f[y][x] = EDGE
    if lid:
        for x in range(w):
            f[0][x] = EDGE
    return f


def side(d, h, rng, lid):
    """A narrow side: the zip runs up the middle (it goes round the case)."""
    f = [[noise(SHELL, rng) for _ in range(d)] for _ in range(h)]
    m = d // 2
    for y in range(h):
        f[y][0] = f[y][d - 1] = EDGE
        f[y][m - 1] = ZIP_TAPE
        f[y][m] = ZIP if y % 2 == 0 else ZIP_TAPE
    if lid:
        for x in range(d):
            f[0][x] = EDGE
    else:
        f[h - 1][1] = f[h - 1][d - 2] = WHEEL
    return f


def top(w, d, rng):
    """The lid's top: the end of the case, with the carry handle."""
    f = [[noise(SHELL, rng) for _ in range(w)] for _ in range(d)]
    for x in range(w):
        f[0][x] = f[d - 1][x] = EDGE
    for y in range(d):
        f[y][0] = f[y][w - 1] = EDGE
    centres = [w // 2] if w < 20 else [w // 4, 3 * w // 4]
    for c in centres:
        for x in range(c - 3, c + 3):         # carry handle across the middle
            f[d // 2][x] = HANDLE
            f[d // 2 + 1][x] = HANDLE_DARK
        for y in (2, 3):                       # telescopic handle tubes at the back
            f[y][c - 3] = f[y][c + 2] = HANDLE_DARK
        if w >= 20:
            for y in range(d):
                f[y][w // 2 - 1] = f[y][w // 2] = EDGE
    return f


def paint(px, x0, y0, f):
    for y, row in enumerate(f):
        for x, c in enumerate(row):
            px[x0 + x, y0 + y] = c + (255,)


def fill(px, x0, y0, w, h, c):
    for y in range(h):
        for x in range(w):
            px[x0 + x, y0 + y] = c + (255,)


def texture(w):
    """w = 14 for a chest, 30 for a double chest; depth 14."""
    d = 14
    img = Image.new("RGBA", (64 if w == 14 else 128, 64), (0, 0, 0, 0))
    px = img.load()
    rng = random.Random(w)
    # lid: box UV at (0, 0), height 5
    paint(px, d, 0, top(w, d, rng))
    fill(px, d + w, 0, w, d, INSIDE)
    for i, (x0, ww) in enumerate(((0, d), (d, w), (d + w, d), (2 * d + w, w))):
        f = side(d, 5, rng, True) if i % 2 == 0 else front(w, 5, rng, True)
        paint(px, x0, d, f)
    # base: box UV at (0, 19), height 10
    fill(px, d, 19, w, d, INSIDE)
    fill(px, d + w, 19, w, d, EDGE)
    for i, (x0, ww) in enumerate(((0, d), (d, w), (d + w, d), (2 * d + w, w))):
        f = side(d, 10, rng, False) if i % 2 == 0 else front(w, 10, rng, False)
        paint(px, x0, 19 + d, f)
    # latch: box UV at (0, 0), 2 x 4 x 1 -> a small lock badge
    fill(px, 0, 0, 6, 5, BADGE)
    for y in range(1, 5):
        px[0, y] = px[5, y] = (110, 114, 118, 255)
    return img


def box_uv(u, v, w, h, d):
    def f(x, y, a, b):
        return {"uv": [x, y], "uv_size": [a, b]}
    return {"up": f(u + d, v, w, d), "down": f(u + d + w, v, w, d),
            "east": f(u, v + d, d, h), "north": f(u + d, v + d, w, h),
            "west": f(u + d + w, v + d, d, h), "south": f(u + 2 * d + w, v + d, w, h)}


def geo(ident, w, tw):
    x0 = -w / 2
    return {"description": {"identifier": ident, "texture_width": tw, "texture_height": 64},
            "bones": [{"name": "chest", "pivot": [0, 0, 0], "cubes": [
                {"origin": [x0, 0, -7], "size": [w, 10, 14], "uv": box_uv(0, 19, w, 10, 14)},
                {"origin": [x0, 9, -7], "size": [w, 5, 14], "uv": box_uv(0, 0, w, 5, 14)},
                {"origin": [-1, 7, 7], "size": [2, 4, 1], "uv": box_uv(0, 0, 2, 4, 1)},
            ]}]}


texture(14).save(HERE / "chest.png")
texture(30).save(HERE / "chest_double.png")
(HERE / "chest_preview.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": [
    geo("geometry.chest_preview", 14, 64), geo("geometry.chest_double_preview", 30, 128)]}, indent=1) + "\n",
    encoding="utf-8")

# ---------- preview sheet ----------
FLOOR = {"up": "#cfc8bb", "south": "#bdb6a9", "north": "#bdb6a9", "east": "#aba497", "west": "#aba497", "down": "#99928a"}


def floor(xs, zs):
    return [{"type": "block", "color": FLOOR, "origin": [x - 8, -16, z - 8], "size": [16, 16, 16]} for x in xs for z in zs]


def chest(x, z, double=False, rot=0):
    return {"type": "geo", "geo": f"{REL}/chest_preview.geo.json",
            "identifier": "geometry.chest_double_preview" if double else "geometry.chest_preview",
            "texture": f"{REL}/{'chest_double' if double else 'chest'}.png",
            "position": [x, 0, z], "rotationY": rot}


sheet = {
    "title": "黑色行李箱：儲物箱換材質（草稿）",
    "columns": 3, "panelWidth": 380, "panelHeight": 320, "background": "#e8edf1",
    "panels": [
        {"label": "正面（硬殼的直條紋）", "camera": {"azimuth": 30, "elevation": 22, "size": 30, "target": [0, 7, 0]},
         "objects": floor([0], [0]) + [chest(0, 0)]},
        {"label": "側面（中間一圈拉鍊）、上面（提把）", "camera": {"azimuth": 120, "elevation": 40, "size": 30, "target": [0, 7, 0]},
         "objects": floor([0], [0]) + [chest(0, 0)]},
        {"label": "大箱子：兩個並排", "camera": {"azimuth": 25, "elevation": 22, "size": 46, "target": [8, 7, 0]},
         "objects": floor([0, 16], [0]) + [{**chest(8, 0, True)}]},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote chest.png, chest_double.png, chest_preview.geo.json, preview.json")
