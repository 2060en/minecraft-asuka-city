"""Build the suitcase draft: textures that replace the chest.

Run from the repository root:
    python3 addon/drafts/suitcase/build.py

Resource pack only: chest.png replaces textures/entity/chest/normal.png and
chest_double.png replaces double_normal.png, so every chest (the author has
few that matter, 2026-11-03) looks like an aluminium suitcase standing
upright, and a double chest like two of them side by side. (The first
draft was a black hard-shell case; the author asked for aluminium.) The
shape cannot change: a chest stays 14 x 15 x 14. The trapped chest
and the ender chest keep their own textures. The vanilla export is simply
the chest.

The vanilla chest model is a 14 x 10 x 14 base under a 14 x 5 x 14 lid,
plus a 2 x 4 x 1 latch on the front, all on box UVs: lid at (0, 0), base at
(0, 19), latch at (0, 0) (bedrock-samples, 2026-11). The double chest is the
same with a width of 30. All four sides get the light horizontal ribs and
grey frame corners, the zip runs round the opening between lid and base, the
latch is the lock, and the lid top carries the handle.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/suitcase"

# Second version (author, 2026-11-03): an aluminium case. Grey frame edges,
# light horizontal ribs, the zip round the opening (the seam between lid and
# base, where the chest opens), a darker grey lock.
BODY = (192, 196, 201)
RIB_HI = (222, 225, 229)         # the raised horizontal ribs
RIB_LO = (168, 172, 178)         # the shadow under each rib
FRAME = (132, 137, 143)
ZIP = (84, 88, 94)
ZIP_TEETH = (150, 154, 160)
LOCK = (74, 78, 84)
LOCK_HI = (110, 114, 120)
HANDLE = (70, 74, 80)
HANDLE_HI = (104, 108, 114)
WHEEL = (40, 41, 44)
LINING = (44, 52, 74)            # navy fabric lining, seen when the case opens
LINING_LO = (36, 42, 62)
STRAP = (150, 154, 160)
BUCKLE = (200, 204, 208)


def noise(c, rng):
    d = rng.randint(-2, 2)
    return tuple(max(0, min(255, v + d)) for v in c)


def wall(w, h, rng, lid, panels=1):
    """A side of the case, row 0 at the top. The lid is the top 5 rows of
    the 15 and the base the other 10; the zip runs along the lid's bottom
    row, which is the opening."""
    f = [[noise(BODY, rng) for _ in range(w)] for _ in range(h)]
    ribs = (2,) if lid else (2, 5)           # light ribs with a shadow line under them
    for y in ribs:
        for x in range(w):
            f[y][x] = noise(RIB_HI, rng)
            f[y + 1][x] = noise(RIB_LO, rng)
    cuts = [0, w - 1] + ([w // 2 - 1, w // 2] if panels == 2 else [])
    for y in range(h):                       # grey frame up the corners
        for x in cuts:
            f[y][x] = FRAME
    if lid:
        for x in range(w):
            f[0][x] = FRAME                  # top edge
            f[h - 1][x] = ZIP_TEETH if x % 2 else ZIP   # the zip at the opening
    else:
        for x in range(w):
            f[0][x] = ZIP                    # the other half of the zip
            f[h - 1][x] = FRAME              # bottom edge
        for x in cuts[:2]:                   # small wheels in the bottom corners
            f[h - 1][x] = WHEEL
    return f


def front(w, h, rng, lid):
    return wall(w, h, rng, lid, panels=2 if w >= 20 else 1)


def side(d, h, rng, lid):
    return wall(d, h, rng, lid)


def top(w, d, rng):
    """The lid's top: frame round the edge, a plain panel, the carry handle."""
    f = [[noise(BODY, rng) for _ in range(w)] for _ in range(d)]
    for x in range(w):
        f[0][x] = f[d - 1][x] = FRAME
    for y in range(d):
        f[y][0] = f[y][w - 1] = FRAME
    centres = [w // 2] if w < 20 else [w // 4, 3 * w // 4]
    for c in centres:
        # carry handle, a "ㄇ" seen from above (author, 2026-11-03: the first
        # one, a plain bar, looked like a coin slot): the grip across the
        # middle, the two feet turned down at its ends, a shadow under the grip.
        y = d // 2 - 1
        for x in range(c - 3, c + 3):
            f[y][x] = HANDLE_HI
            f[y + 1][x] = noise(RIB_LO, rng)
        for x in (c - 3, c + 2):
            f[y + 1][x] = HANDLE
            f[y + 2][x] = HANDLE
    if w >= 20:
        for y in range(d):
            f[y][w // 2 - 1] = f[y][w // 2] = FRAME
    return f


def inside(w, d, rng, lid):
    """The inside, seen when the chest opens: the base's top or the lid's
    underside. The zip runs round the rim (the opening); inside is a navy
    lining, with two straps and buckles in the base and a zipped pocket in
    the lid (author, 2026-11-03: it was plain grey)."""
    f = [[(LINING if (x + y) % 3 else LINING_LO) for x in range(w)] for y in range(d)]
    f = [[noise(c, rng) for c in row] for row in f]
    for x in range(w):
        f[0][x] = f[d - 1][x] = ZIP_TEETH if x % 2 else ZIP
    for y in range(d):
        f[y][0] = f[y][w - 1] = ZIP_TEETH if y % 2 else ZIP
    halves = [(1, w - 1)] if w < 20 else [(1, w // 2 - 1), (w // 2 + 1, w - 1)]
    if w >= 20:
        for y in range(d):
            f[y][w // 2 - 1] = f[y][w // 2] = FRAME
    for a, b in halves:
        if lid:                              # a zipped pocket across the lid
            for x in range(a + 1, b - 1):
                f[d // 2][x] = ZIP_TEETH if x % 2 else ZIP
        else:                                # two straps with buckles
            for x in (a + (b - a) // 3, a + 2 * (b - a) // 3):
                for y in range(1, d - 1):
                    f[y][x] = STRAP
                f[d // 2][x] = BUCKLE
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
    paint(px, d + w, 0, inside(w, d, rng, True))    # lid underside
    for i, (x0, ww) in enumerate(((0, d), (d, w), (d + w, d), (2 * d + w, w))):
        f = side(d, 5, rng, True) if i % 2 == 0 else front(w, 5, rng, True)
        paint(px, x0, d, f)
    # base: box UV at (0, 19), height 10
    paint(px, d, 19, inside(w, d, rng, False))      # base top
    fill(px, d + w, 19, w, d, FRAME)
    for i, (x0, ww) in enumerate(((0, d), (d, w), (d + w, d), (2 * d + w, w))):
        f = side(d, 10, rng, False) if i % 2 == 0 else front(w, 10, rng, False)
        paint(px, x0, 19 + d, f)
    # latch: box UV at (0, 0), 2 x 4 x 1 -> the dark grey lock
    fill(px, 0, 0, 6, 5, LOCK)
    px[1, 2] = px[2, 2] = LOCK_HI + (255,)
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
# The chest's icon in the inventory is drawn from three block textures
# (chest_front, chest_side, chest_top), not from this model. v0.7.1 replaced
# them too, but the trapped chest shares the side and top, so it changed with
# them; the author chose to keep the vanilla chest icon (2026-11-04).
texture(30).save(HERE / "chest_double.png")
opened = geo("geometry.chest_open_preview", 14, 64)
for c in opened["bones"][0]["cubes"][1:]:      # the lid and the latch swing open at the back edge
    c["pivot"], c["rotation"] = [0, 10, -7], [-100, 0, 0]
(HERE / "chest_preview.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": [
    geo("geometry.chest_preview", 14, 64), geo("geometry.chest_double_preview", 30, 128), opened]}, indent=1) + "\n",
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
    "title": "鋁製行李箱：儲物箱換材質（第二版草稿）",
    "columns": 2, "panelWidth": 480, "panelHeight": 320, "background": "#e8edf1",
    "panels": [
        {"label": "正面（橫條紋、深灰色的鎖）", "camera": {"azimuth": 30, "elevation": 22, "size": 30, "target": [0, 7, 0]},
         "objects": floor([0], [0]) + [chest(0, 0)]},
        {"label": "拉鍊在箱子的開口一圈、上面提把", "camera": {"azimuth": 120, "elevation": 40, "size": 30, "target": [0, 7, 0]},
         "objects": floor([0], [0]) + [chest(0, 0)]},
        {"label": "打開：拉鍊一圈、深藍色內襯、綁帶與夾層", "camera": {"azimuth": 20, "elevation": 50, "size": 34, "target": [0, 9, 0]},
         "objects": floor([0], [0]) + [{**chest(0, 0), "identifier": "geometry.chest_open_preview"}]},
        {"label": "大箱子：兩個並排", "camera": {"azimuth": 25, "elevation": 22, "size": 46, "target": [8, 7, 0]},
         "objects": floor([0, 16], [0]) + [{**chest(8, 0, True)}]},
    ],
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote chest.png, chest_double.png, chest_preview.geo.json, preview.json")
