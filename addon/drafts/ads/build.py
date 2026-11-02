"""Build the advertisement paintings.

Run from the repository root:
    python3 addon/drafts/ads/build.py [--vanilla DIR]

Resource pack only. Each replaceable painting (docs/ads.md) can get an
advertisement; the vanilla export is simply the paintings.

Decided 2026-11-01: advertisements are drawn at 32x (32 px per block), so
small posters can carry a line of kanji. The classic paintings share one
atlas, textures/painting/kz.png, which becomes 512 x 512; the laptop screens
and lid (addon/drafts/laptop/kz_overlay.png, 16x) are enlarged 2x with
nearest-neighbour and look the same. The paintings added in 1.21 are one file
each; only those with an advertisement are replaced, at 32x.

Outputs, all in this folder:
- kz_overlay.png: 512 x 512, the laptop parts plus every advertisement,
  transparent elsewhere
- painting/<name>.png: the 1.21 paintings that have an advertisement
- preview_atlas.png, preview.geo.json, preview.json: the preview sheet

With --vanilla DIR (a folder holding the vanilla textures/painting files, for
example from https://github.com/Mojang/bedrock-samples), it also writes the
complete kz.png to addon/build/textures/painting/: vanilla enlarged 2x, then
the overlay on top. addon/build/ is not committed, so no vanilla image ends
up in the repository.

Whether the game shows a 512 x 512 kz.png and 32x single paintings correctly
needs a test in game.
"""
import argparse
import json
from pathlib import Path

from PIL import Image

import ads_2x1
from samples import SAMPLES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REL = "/addon/drafts/ads"
K = 32                       # pixels per block

# ---------- painting slots (docs/ads.md) ----------
# code: (w, h, file, (x, y) in the 16x kz.png or None for a file of its own)
SLOTS = {
    "A1": (2, 1, "kz", (0, 32)), "A2": (2, 1, "kz", (32, 32)), "A3": (2, 1, "kz", (64, 32)),
    "A4": (2, 1, "kz", (96, 32)), "A5": (2, 1, "kz", (128, 32)),
    "B1": (1, 2, "kz", (0, 64)), "B2": (1, 2, "kz", (16, 64)), "B3": (1, 2, "prairie_ride", None),
    "C1": (2, 2, "kz", (0, 128)), "C2": (2, 2, "kz", (32, 128)), "C3": (2, 2, "kz", (64, 128)),
    "C4": (2, 2, "kz", (96, 128)), "C5": (2, 2, "kz", (128, 128)), "C6": (2, 2, "kz", (160, 128)),
    "C7": (2, 2, "baroque", None), "C8": (2, 2, "humble", None),
    "D1": (3, 3, "bouquet", None), "D2": (3, 3, "cavebird", None), "D3": (3, 3, "cotan", None),
    "D4": (3, 3, "endboss", None), "D5": (3, 3, "fern", None), "D6": (3, 3, "owlemons", None),
    "D7": (3, 3, "sunflowers", None), "D8": (3, 3, "tides", None),
    "E1": (4, 2, "kz", (0, 96)), "E2": (4, 2, "changing", None), "E3": (4, 2, "finding", None),
    "E4": (4, 2, "lowmist", None), "E5": (4, 2, "passage", None),
    "F1": (3, 4, "backyard", None), "F2": (3, 4, "pond", None),
    "G1": (4, 3, "kz", (192, 64)), "G2": (4, 3, "kz", (192, 112)),
    "H1": (4, 4, "kz", (0, 192)), "H2": (4, 4, "kz", (64, 192)), "H3": (4, 4, "kz", (128, 192)),
    "H4": (4, 4, "orb", None), "H5": (4, 4, "unpacked", None),
    "X1": (2, 2, "kz", (0, 160)), "X2": (2, 2, "kz", (32, 160)), "X3": (2, 2, "kz", (64, 160)),
    "X4": (2, 2, "kz", (96, 160)),
}

# code: draw function returning a (w * 32) x (h * 32) RGBA image, one
# module per size. Drawn one at a time with the author (2026-11-02).
ADS = {**ads_2x1.ADS}
TITLES = {**ads_2x1.TITLES}

# ---------- textures ----------
laptop = Image.open(ROOT / "addon/drafts/laptop/kz_overlay.png")
overlay = laptop.resize((512, 512), Image.NEAREST)
singles = {}
drawn = {}
hd = {}
(HERE / "hd").mkdir(exist_ok=True)
for code, draw in ADS.items():
    w, h, file, pos = SLOTS[code]
    img = draw(1)
    assert img.size == (w * K, h * K), (code, img.size)
    drawn[code] = img
    hd[code] = draw(2)                       # the 64x spare, one step finer
    assert hd[code].size == (w * K * 2, h * K * 2), (code, hd[code].size)
    hd[code].save(HERE / "hd" / f"{code}.png")
    if pos:
        x, y = pos
        assert not overlay.crop((2 * x, 2 * y, 2 * x + w * K, 2 * y + h * K)).getbbox(), f"{code} would cover the laptop"
        overlay.paste(img, (2 * x, 2 * y))
    else:
        singles[file] = img
overlay.save(HERE / "kz_overlay.png")
(HERE / "painting").mkdir(exist_ok=True)
for old in (HERE / "painting").glob("*.png"):
    if old.stem not in singles:
        old.unlink()
for file, img in singles.items():
    img.save(HERE / "painting" / f"{file}.png")

parser = argparse.ArgumentParser()
parser.add_argument("--vanilla", type=Path, help="folder with the vanilla textures/painting files")
parser.add_argument("--focus", help="slot code the preview shows (default: the last one registered)")
args = parser.parse_args()
if args.vanilla:
    out = ROOT / "addon/build/textures/painting"
    out.mkdir(parents=True, exist_ok=True)
    full = Image.open(args.vanilla / "kz.png").convert("RGBA").resize((512, 512), Image.NEAREST)
    full.alpha_composite(overlay)
    full.save(out / "kz.png")
    for file, img in singles.items():
        img.save(out / f"{file}.png")
    print(f"wrote {out.relative_to(ROOT)}/kz.png and {len(singles)} single paintings")

# ---------- preview atlas: 64 px per block, so the 64x spares fit ----------
AK = 64
lid = laptop.crop((192, 0, 208, 16)).resize((AK, AK), Image.NEAREST)
entries = [(f"ad_{code}", *SLOTS[code][:2], img.resize((img.width * 2, img.height * 2), Image.NEAREST))
           for code, img in drawn.items()]
entries += [(f"hd_{code}", *SLOTS[code][:2], img) for code, img in hd.items()]
entries += [(f"sample_{name}", w, h, draw().resize((w * AK, h * AK), Image.NEAREST)) for name, label, w, h, draw in SAMPLES]

ATLAS_W = 1024
x = y = row_h = 0
placed = {}
for name, w, h, img in entries + [("lid", 1, 1, lid)]:
    if x + img.width > ATLAS_W:
        x, y, row_h = 0, y + row_h, 0
    placed[name] = (x, y, img)
    x += img.width
    row_h = max(row_h, img.height)
ATLAS_H = y + row_h
atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
for name, (ax, ay, img) in placed.items():
    atlas.paste(img, (ax, ay))
atlas.save(HERE / "preview_atlas.png")

# ---------- preview models: a w x h painting, 1 pixel thick ----------
lx, ly, _ = placed["lid"]
back = {"uv": [lx, ly], "uv_size": [AK, AK]}
edge = {"uv": [lx + 4, ly + 4], "uv_size": [1, 1]}
geos = []
for name, w, h, img in entries:
    ax, ay, _ = placed[name]
    geos.append({
        "description": {"identifier": f"geometry.{name}", "texture_width": ATLAS_W, "texture_height": ATLAS_H},
        "bones": [{"name": "painting", "pivot": [0, 0, 0], "cubes": [{
            "origin": [-8, 0, -8], "size": [16 * w, 16 * h, 1],
            "uv": {"south": {"uv": [ax, ay], "uv_size": [w * AK, h * AK]}, "north": back,
                   "east": edge, "west": edge, "up": edge, "down": edge},
        }]}],
    })
(HERE / "preview.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos}, indent=1) + "\n",
                                       encoding="utf-8")


# ---------- scenes ----------
def shades(top, side, front):
    return {"up": top, "down": side, "east": side, "west": side, "south": front, "north": front}


CREAM = shades("#efe9dc", "#d9d1c0", "#e6dfd0")
GLASS = shades("#bcd6e6", "#9fbccf", "#a9c8dc")
CEIL = shades("#f4f4f2", "#dcdcda", "#e8e8e6")
SEAT = shades("#4d6aa8", "#3d5790", "#45609c")
FLOOR = shades("#8a8f96", "#73787f", "#7e838a")
TILE = shades("#f2f3f4", "#d7d9dc", "#e6e8ea")
PLATFORM = shades("#b9b4aa", "#9d988e", "#aaa59b")


def block(x, y, z, color, size=(16, 16, 16)):
    return {"type": "block", "color": color, "origin": [x - 8, y, z - 8], "size": list(size)}


def painting(name, x, y, z=16):
    """Hang a painting on the south face of the wall at z = 0; x is the centre
    of its leftmost block, y the bottom."""
    return {"type": "geo", "geo": f"{REL}/preview.geo.json", "identifier": f"geometry.{name}",
            "texture": f"{REL}/preview_atlas.png", "position": [x, y, z]}


def train_car(ads):
    """Inside a commuter car: seats, windows, and the advert band above them."""
    objs = []
    for x in range(-88, 89, 16):
        for z in (0, 16, 32):
            objs.append(block(x, -16, z, FLOOR))
        objs.append(block(x, 0, 0, CREAM))
        objs.append(block(x, 16, 0, GLASS))
        objs.append(block(x, 32, 0, CREAM))
        objs.append(block(x, 48, 0, CEIL))
        objs.append(block(x, 0, 16, SEAT, (16, 7, 16)))
    for x in (-72, -24, 24, 72):
        objs.append(block(x, 16, 0, CREAM))          # window posts
    objs += [painting(name, x, 32) for name, x in zip(ads, (-56, -8, 40))]
    return objs


def station(placements):
    """A tiled station wall; placements are (name, x, y)."""
    objs = []
    for x in range(-88, 89, 16):
        for z in (16, 32, 48):
            objs.append(block(x, -16, z, PLATFORM))
        for y in (-16, 0, 16, 32, 48):
            objs.append(block(x, y, 0, TILE))
    objs += [painting(name, x, y) for name, x, y in placements]
    return objs


def flat(placements):
    objs = [block(x, y, 0, TILE) for x in range(-56, 57, 16) for y in (0, 16, 32)]
    objs += [painting(name, x, y) for name, x, y in placements]
    return objs


SHELF = shades("#d9dcdf", "#b9bcc0", "#c9ccd0")
GOODS = ["#e05a4f", "#f2c14e", "#5aa0d8", "#6cbf7a", "#f08a3c", "#9b7fd1", "#ffffff", "#3c4a5c"]


def shop(name):
    """A convenience-store wall: shelves of goods, the advert above them."""
    objs = []
    for x in range(-56, 57, 16):
        for z in (16, 32, 48):
            objs.append(block(x, -16, z, TILE))
        for y in (0, 16, 32, 48):
            objs.append(block(x, y, 0, TILE))
    for x in range(-40, 41, 16):
        for y in (0, 14):
            objs.append(block(x, y, 16, SHELF, (16, 2, 12)))
        for i, gx in enumerate(range(x - 7, x + 7, 4)):
            for y in (2, 16):
                c = GOODS[(i + x // 16 + y) % len(GOODS)]
                objs.append({"type": "block", "color": shades(c, c, c), "origin": [gx, y, 12], "size": [3, 6 + (i % 2) * 2, 4]})
        objs.append(block(x, 28, 16, SHELF, (16, 2, 12)))
    objs.append(painting(name, -8, 32))
    return objs


args_focus = args.focus or (list(ADS)[-1] if ADS else None)
panels = []
if args_focus:
    code = args_focus
    w, h = SLOTS[code][:2]
    name = f"ad_{code}"
    same = [f"ad_{c}" for c in ADS if SLOTS[c][:2] == (w, h)]
    panels.append({"label": f"{code}（平面）", "camera": {"azimuth": 0, "elevation": 0, "size": 16 * h + 6,
                                                       "target": [16 * w / 2 - 16, 32 + 8 * h, 16]},
                   "objects": flat([(name, -8, 32)])})
    hd_panel = {"label": f"{code} 的 64x 備用版（平面）", "camera": {"azimuth": 0, "elevation": 0, "size": 16 * h + 6,
                                                            "target": [16 * w / 2 - 16, 32 + 8 * h, 16]},
                "objects": flat([(f"hd_{code}", -8, 32)])}
    if (w, h) == (2, 1):
        others = [n for n in same if n != name] + ["sample_air"]
        panels.append({"label": "鐵路車廂：窗上", "camera": {"azimuth": 18, "elevation": 6, "size": 72, "target": [-8, 26, 16]},
                       "objects": train_car([others[0], name, others[-1]])})
        panels.append({"label": "店頭：貨架上方", "camera": {"azimuth": 25, "elevation": 12, "size": 64, "target": [0, 24, 16]},
                       "objects": shop(name)})
        panels.append({"label": "車廂裡近看", "camera": {"azimuth": 30, "elevation": -8, "size": 30, "target": [0, 40, 16]},
                       "objects": train_car([others[0], name, others[-1]])})
    panels.insert(1, hd_panel)
    title = f"{code}：{TITLES.get(code, '')}（草稿）"
else:
    samples = [
        ("sample_air", -56, 32), ("sample_snow", -56, 0), ("sample_express", -24, 0),
    ]
    panels.append({"label": "樣品（平面）", "camera": {"azimuth": 0, "elevation": 0, "size": 58, "target": [-16, 24, 16]},
                   "objects": flat(samples)})
    panels.append({"label": "車廂：窗上的 2 × 1 廣告", "camera": {"azimuth": 18, "elevation": 6, "size": 72, "target": [-8, 26, 16]},
                   "objects": train_car(["sample_air"] * 3)})
    panels.append({"label": "車站牆面：1 × 2 海報與 4 × 2 看板", "camera": {"azimuth": 22, "elevation": 8, "size": 80, "target": [0, 20, 16]},
                   "objects": station([("sample_snow", -72, 16), ("sample_express", -40, 16),
                                       ("sample_snow", 40, 16), ("sample_air", 72, 32)])})
    panels.append({"label": "Asuka Air 的標誌（放大）", "camera": {"azimuth": 0, "elevation": 0, "size": 22, "target": [-48, 40, 16]},
                   "objects": flat(samples)})
    title = "廣告樣品（32x）：Asuka Air 改用品牌的黑白與黒潮標誌。內容等作者填 docs/ads.md"

sheet = {
    "title": title,
    "columns": 2, "panelWidth": 600, "panelHeight": 330, "background": "#e8edf1",
    "panels": panels,
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"wrote kz_overlay.png, {len(singles)} single paintings, preview files" + (f" (focus {args_focus})" if args_focus else ""))
