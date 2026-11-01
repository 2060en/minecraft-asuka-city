"""Build the advertisement paintings draft.

Run from the repository root:
    python3 addon/drafts/ads/build.py

Resource pack only. Each replaceable painting (docs/ads.md) gets an
advertisement; the vanilla export is simply the paintings.

Stage 1 (now): the content of docs/ads.md is still open, so this builds three
sample advertisements at 16x and 32x side by side, hung as 1-pixel-thick
paintings in a train car and on a station wall, to decide the resolution.

Preview models: a painting is a w x h block slab, 1 pixel thick. Its front is
the advertisement; the back and the sides use the shared painting back,
which is the laptop lid (addon/drafts/laptop/kz_overlay.png at (192, 0)).
The preview atlas is drawn at 32 px per block; 16x art is enlarged 2x with
nearest-neighbour, which is how the game would show it.
"""
import json
from pathlib import Path

from PIL import Image

from samples import SAMPLES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REL = "/addon/drafts/ads"
K = 32                       # atlas pixels per block

lid = Image.open(ROOT / "addon/drafts/laptop/kz_overlay.png").crop((192, 0, 208, 16)).resize((K, K), Image.NEAREST)

# ---------- preview atlas ----------
entries = []                 # (name, w, h, image at K px per block)
for i, (label, w, h, draws) in enumerate(SAMPLES):
    for res, draw in draws.items():
        img = draw()
        assert img.size == (16 * w * res // 16, 16 * h * res // 16), (label, res, img.size)
        entries.append((f"s{i}_{res}", w, h, img.resize((w * K, h * K), Image.NEAREST)))

ATLAS_W = 512
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

# ---------- preview models ----------
lx, ly, _ = placed["lid"]
back = {"uv": [lx, ly], "uv_size": [K, K]}
edge = {"uv": [lx + 2, ly + 2], "uv_size": [1, 1]}
geos = []
for name, w, h, img in entries:
    ax, ay, _ = placed[name]
    geos.append({
        "description": {"identifier": f"geometry.{name}", "texture_width": ATLAS_W, "texture_height": ATLAS_H},
        "bones": [{"name": "painting", "pivot": [0, 0, 0], "cubes": [{
            "origin": [-8, 0, -8], "size": [16 * w, 16 * h, 1],
            "uv": {"south": {"uv": [ax, ay], "uv_size": [w * K, h * K]}, "north": back,
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


def train_car(res):
    """Inside a commuter car: seats, windows, and the advert band above them."""
    objs = []
    xs = range(-88, 89, 16)
    for x in xs:
        objs.append(block(x, -16, 0, FLOOR))
        objs.append(block(x, -16, 16, FLOOR))
        objs.append(block(x, -16, 32, FLOOR))
        objs.append(block(x, 0, 0, CREAM))
        objs.append(block(x, 16, 0, GLASS))
        objs.append(block(x, 32, 0, CREAM))
        objs.append(block(x, 48, 0, CEIL))
        objs.append(block(x, 0, 16, SEAT, (16, 7, 16)))
    for x in (-72, -24, 24, 72):
        objs.append(block(x, 16, 0, CREAM))          # window posts
    objs += [painting(f"s0_{res}", x, 32) for x in (-56, -8, 40)]
    return objs


def station(res):
    """A station wall with tiled panels: two vertical posters and a billboard."""
    objs = []
    for x in range(-88, 89, 16):
        for z in (16, 32, 48):
            objs.append(block(x, -16, z, PLATFORM))
        for y in (-16, 0, 16, 32, 48):
            objs.append(block(x, y, 0, TILE))
    objs.append(painting(f"s1_{res}", -72, 16))
    objs.append(painting(f"s2_{res}", -40, 16))
    objs.append(painting(f"s1_{res}", 40, 16))
    objs.append(painting(f"s0_{res}", 72, 32))
    return objs


def flat(res):
    objs = [block(x, y, 0, TILE) for x in range(-56, 57, 16) for y in (0, 16, 32)]
    objs.append(painting(f"s0_{res}", -56, 32))
    objs.append(painting(f"s1_{res}", -56, 0))
    objs.append(painting(f"s2_{res}", -24, 0))
    return objs


panels = []
for title, scene, cam in (
    ("平面", flat, {"azimuth": 0, "elevation": 0, "size": 58, "target": [-16, 24, 16]}),
    ("車廂：窗上的 2 × 1 廣告", train_car, {"azimuth": 18, "elevation": 6, "size": 72, "target": [-8, 26, 16]}),
    ("車站牆面：1 × 2 海報與 4 × 2 看板", station, {"azimuth": 22, "elevation": 8, "size": 80, "target": [0, 20, 16]}),
):
    for res in (16, 32):
        panels.append({"label": f"{title}（{res}x）", "camera": cam, "objects": scene(res)})

sheet = {
    "title": "廣告的解析度比較：左 16x（原版的細緻度），右 32x（字比較清楚）。內容只是樣品",
    "columns": 2, "panelWidth": 600, "panelHeight": 330, "background": "#e8edf1",
    "panels": panels,
}
(HERE / "preview.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote preview_atlas.png, preview.geo.json, preview.json")
