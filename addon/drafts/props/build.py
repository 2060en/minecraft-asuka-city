"""Build the small retexture drafts of the second batch (2026-11-03).

Run from the repository root:
    python3 addon/drafts/props/build.py

Resource pack only; removing the pack brings back the vanilla look.

Some of these start from the vanilla texture and change only part of it, as
the author asked (the cushion keeps its fabric, the wither skeleton skull
keeps its three sides). Those are made from the vanilla files, downloaded
from Mojang's bedrock-samples into addon/build/vanilla/, and written to
addon/build/drafts/props/, which is not committed: no vanilla image in the
repository. addon/pack/build.py runs make_all() the same way.

    cushion            the button in the middle of the top and bottom goes,
                       all 16 colours (entity/cushion/<colour>_cushion.png)
    flower pot         white ceramic, block and item
    decorated pot      white steel, like a metal can; sherd sides untouched
    wither skull       the face becomes the same as the other three sides
    pale oak shelf     steel shelf
    milk bucket        the item icon becomes a milk carton (drawn here)
"""
import json
import random
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VANILLA = ROOT / "addon" / "build" / "vanilla"
OUT = ROOT / "addon" / "build" / "drafts" / "props"
SAMPLES = "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/"

COLOURS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
           "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"]


def vanilla(path):
    cache = VANILLA / path
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SAMPLES + path, cache)
    return Image.open(cache).convert("RGBA")


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def recolour(img, low, high, seed, streaks=0):
    """Keep the shading of a vanilla texture but move it into a new colour
    range: the darkest pixel becomes `low`, the lightest `high`. `streaks`
    adds a faint horizontal brushed-steel grain."""
    px = img.load()
    ls = [lum(px[x, y]) for y in range(img.height) for x in range(img.width) if px[x, y][3]]
    lo, hi = min(ls), max(ls)
    rng = random.Random(seed)
    rows = {y: rng.choice((-3, 0, 0, 2, 3)) for y in range(img.height)} if streaks else {}
    out = img.copy()
    po = out.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            t = (lum((r, g, b)) - lo) / max(1, hi - lo)
            d = rows.get(y, 0) * streaks + rng.randint(-1, 1) * streaks
            po[x, y] = tuple(max(0, min(255, round(l + (h - l) * t + d))) for l, h in zip(low, high)) + (a,)
    return out


# ---------- cushion: no button ----------
def cushion(colour):
    img = vanilla(f"textures/entity/cushion/{colour}_cushion.png")
    px = img.load()
    rng = random.Random(colour)
    for fx in (16, 32):                     # top and bottom faces, 16 x 16 at (fx, 0)
        face = [px[fx + x, y] for y in range(16) for x in range(16)]
        common = sorted(set(face), key=face.count, reverse=True)[:2]   # the plain fabric
        # the button and the creases meeting at it: the 4 x 4 in the middle
        for y in range(6, 10):
            for x in range(6, 10):
                px[fx + x, y] = rng.choice(common)
    return img


# ---------- wither skeleton skull: no face ----------
def wither_skull():
    img = vanilla("textures/entity/skulls/wither_skeleton.png")
    side = img.crop((24, 8, 32, 16))        # the back of the head (box UV, 8 x 8 x 8 at 0, 0)
    img.paste(side, (8, 8))                 # over the face
    return img


# ---------- milk carton (drawn from scratch) ----------
def milk_carton():
    W, B, BL, R, G = (244, 245, 246), (196, 200, 206), (58, 110, 186), (118, 168, 222), (70, 74, 82)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()

    def put(x, y, c):
        px[x, y] = c + (255,)
    # gable top: the fin and the two roof slopes
    for x in range(6, 10):
        put(x, 1, B)
    for y, (a, b) in enumerate(((5, 10), (4, 11), (4, 11)), start=2):
        for x in range(a, b + 1):
            put(x, y, W if x < 8 else B)
    # body: front (white) and side (shaded), outline
    for y in range(5, 15):
        for x in range(4, 12):
            put(x, y, W if x < 9 else B)
    for y in range(8, 12):                  # the blue band with a light stripe
        for x in range(4, 12):
            put(x, y, BL if x < 9 else (44, 88, 156))
    for x in range(5, 9):
        put(x, 9, R)
    for y in range(1, 15):                  # outline
        for x in range(3, 13):
            if px[x, y][3] == 0 and any(0 <= x + dx < 16 and px[x + dx, y + dy][3] and px[x + dx, y + dy][:3] != G
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                put(x, y, G)
    for x in range(4, 12):
        put(x, 15, G)
    return img


def make_all(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    made = {}

    def save(img, path):
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest)
        made[path] = dest

    for c in COLOURS:
        save(cushion(c), f"textures/entity/cushion/{c}_cushion.png")
    white = ((196, 198, 200), (246, 247, 248))
    save(recolour(vanilla("textures/blocks/flower_pot.png"), *white, 1), "textures/blocks/flower_pot.png")
    save(recolour(vanilla("textures/items/flower_pot.png"), (120, 122, 126), (248, 248, 248), 2),
         "textures/items/flower_pot.png")
    steel = ((176, 182, 188), (236, 238, 240))
    save(recolour(vanilla("textures/blocks/decorated_pot_side.png"), *steel, 3, streaks=1),
         "textures/blocks/decorated_pot_side.png")
    save(recolour(vanilla("textures/blocks/decorated_pot_base.png"), *steel, 4, streaks=1),
         "textures/blocks/decorated_pot_base.png")
    save(wither_skull(), "textures/entity/skulls/wither_skeleton.png")
    save(recolour(vanilla("textures/blocks/pale_oak_shelf.png"), (98, 104, 112), (206, 211, 216), 5, streaks=1),
         "textures/blocks/pale_oak_shelf.png")
    save(milk_carton(), "textures/items/bucket_milk.png")
    return made


def preview(made):
    """A flat before / after sheet (it holds vanilla images, so it stays in addon/build/)."""
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 18)
    rows = [("坐墊（紅）：中間的點拿掉", "textures/entity/cushion/red_cushion.png", (16, 0, 48, 16)),
            ("坐墊（白）", "textures/entity/cushion/white_cushion.png", (16, 0, 48, 16)),
            ("花盆（方塊）", "textures/blocks/flower_pot.png", (4, 4, 12, 16)),
            ("花盆（物品）", "textures/items/flower_pot.png", None),
            ("陶罐：側面", "textures/blocks/decorated_pot_side.png", None),
            ("陶罐：上下與瓶口", "textures/blocks/decorated_pot_base.png", None),
            ("凋零骷髏頭：臉換成側面", "textures/entity/skulls/wither_skeleton.png", (0, 0, 32, 16)),
            ("蒼白橡木展示架 → 鐵製", "textures/blocks/pale_oak_shelf.png", None),
            ("牛奶桶 → 盒裝牛奶", "textures/items/bucket_milk.png", None)]
    W, H = 900, 150
    sheet = Image.new("RGBA", (W, H * len(rows) + 50), (232, 237, 241, 255))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), "小改材質（草稿）：左原版，右新的", fill=(40, 42, 46), font=font)
    for k, (label, path, box) in enumerate(rows):
        y = 50 + k * H
        d.text((20, y + 60), label, fill=(40, 42, 46), font=font)
        for j, img in enumerate((vanilla(path), Image.open(made[path]).convert("RGBA"))):
            if box:
                img = img.crop(box)
            sc = max(1, min(256 // img.width, 128 // img.height))
            img = img.resize((img.width * sc, img.height * sc), Image.NEAREST)
            sheet.alpha_composite(img, (330 + j * 290, y + 10))
    sheet.save(OUT / "preview.png")


if __name__ == "__main__":
    made = make_all()
    preview(made)
    print(f"wrote {len(made)} textures and preview.png to {OUT.relative_to(ROOT)}/")
