"""Put the author's advertisement images onto the paintings.

Run from the repository root:
    python3 addon/drafts/ads/build.py [--vanilla DIR]

Resource pack only. The author prepares one image per painting slot
(docs/ads.md) and puts it in addon/drafts/ads/images/, named by the slot
code: A1.png, C4.jpg and so on (png, jpg or webp, any size). This script
fits each image to its painting and writes the textures; it does not draw
anything itself (decided 2026-11-02).

Fitting:
- the image is cropped around its centre to the painting's shape (w x h
  blocks) if its shape differs; the script says so;
- it is resized to 32 px per block (32x, decided 2026-11-01). An image that
  is an exact multiple of that size (pixel art) is resized with
  nearest-neighbour, anything else (a photo) with Lanczos;
- a 64x spare of every image goes to hd/ (the author asked for one per ad).

Outputs, all in this folder:
- kz_overlay.png: 512 x 512, the laptop parts (addon/drafts/laptop/, enlarged
  2x) plus every advertisement on a classic painting, transparent elsewhere.
  The laptop parts are never covered: S1 and S2 are refused
- painting/<name>.png: the 1.21 paintings that have an advertisement
- hd/<code>.png: the 64x spares
- preview.png: every advertisement in place, flat, labelled with its code

With --vanilla DIR (a folder holding the vanilla textures/painting files, for
example from https://github.com/Mojang/bedrock-samples), it also writes the
complete kz.png to addon/build/textures/painting/: vanilla enlarged 2x, then
the overlay on top. addon/build/ is not committed, so no vanilla image ends
up in the repository.

Whether the game shows a 512 x 512 kz.png and 32x single paintings correctly
needs a test in game.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGES = HERE / "images"
K = 32                       # pixels per block
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

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
    "S3": (1, 1, "kz", (32, 0)), "S4": (1, 1, "kz", (48, 0)), "S5": (1, 1, "kz", (64, 0)),
    "S6": (1, 1, "kz", (80, 0)), "S7": (1, 1, "kz", (96, 0)), "S8": (1, 1, "meditative", None),
}
LAPTOP = {"S1", "S2"}        # the laptop screens; their slots are taken


def fit(img, w, h, px, code):
    """Crop img around its centre to w:h and resize it to px per block."""
    img = img.convert("RGBA")
    W, H = img.size
    if abs(W * h - H * w) > max(W, H) * 0.01 * min(w, h):
        if W * h > H * w:                    # too wide: trim the sides
            nw = round(H * w / h)
            img = img.crop(((W - nw) // 2, 0, (W - nw) // 2 + nw, H))
        else:                                # too tall: trim top and bottom
            nh = round(W * h / w)
            img = img.crop((0, (H - nh) // 2, W, (H - nh) // 2 + nh))
        if px == K:
            print(f"  {code}: {W} x {H} is not {w}:{h}, cropped around the centre to {img.width} x {img.height}")
    tw, th = w * px, h * px
    exact = img.width % tw == 0 and img.height % th == 0 and img.width // tw == img.height // th
    return img.resize((tw, th), Image.NEAREST if exact else Image.LANCZOS)


parser = argparse.ArgumentParser()
parser.add_argument("--vanilla", type=Path, help="folder with the vanilla textures/painting files")
args = parser.parse_args()

sources = {}
for f in sorted(IMAGES.glob("*")) if IMAGES.exists() else []:
    if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        continue
    code = f.stem.upper()
    if code in LAPTOP:
        raise SystemExit(f"{f.name}: {code} is a laptop screen (addon/drafts/laptop/), not an advertisement slot")
    if code not in SLOTS:
        raise SystemExit(f"{f.name}: no painting slot called {code}; see docs/ads.md")
    if code in sources:
        raise SystemExit(f"two images for {code}: {sources[code].name} and {f.name}")
    sources[code] = f

laptop = Image.open(ROOT / "addon/drafts/laptop/kz_overlay.png")
overlay = laptop.resize((512, 512), Image.NEAREST)
singles, fitted = {}, {}
(HERE / "hd").mkdir(exist_ok=True)
(HERE / "painting").mkdir(exist_ok=True)
for code, f in sources.items():
    w, h, file, pos = SLOTS[code]
    src = Image.open(f)
    img = fit(src, w, h, K, code)
    fitted[code] = img
    fit(src, w, h, K * 2, code).save(HERE / "hd" / f"{code}.png")
    if pos:
        x, y = 2 * pos[0], 2 * pos[1]
        assert not overlay.crop((x, y, x + w * K, y + h * K)).getbbox(), f"{code} would cover the laptop"
        overlay.paste(img, (x, y))
    else:
        singles[file] = img
overlay.save(HERE / "kz_overlay.png")
for old in (HERE / "painting").glob("*.png"):
    if old.stem not in singles:
        old.unlink()
for file, img in singles.items():
    img.save(HERE / "painting" / f"{file}.png")
for old in (HERE / "hd").glob("*.png"):
    if old.stem not in sources:
        old.unlink()

if args.vanilla:
    out = ROOT / "addon/build/textures/painting"
    out.mkdir(parents=True, exist_ok=True)
    full = Image.open(args.vanilla / "kz.png").convert("RGBA").resize((512, 512), Image.NEAREST)
    full.alpha_composite(overlay)
    full.save(out / "kz.png")
    for file, img in singles.items():
        img.save(out / f"{file}.png")
    print(f"wrote {out.relative_to(ROOT)}/kz.png and {len(singles)} single paintings")

# ---------- preview: every advertisement, flat, at 4x ----------
preview = HERE / "preview.png"
if fitted:
    font = ImageFont.truetype(FONT, 16)
    tiles = [(code, img.resize((img.width * 4, img.height * 4), Image.NEAREST)) for code, img in fitted.items()]
    width, pad, label = 1200, 16, 24
    x = y = pad
    row_h, places = 0, []
    for code, tile in tiles:
        if x + tile.width + pad > width and x > pad:
            x, y, row_h = pad, y + row_h + label + pad, 0
        places.append((code, tile, x, y))
        x += tile.width + pad
        row_h = max(row_h, tile.height)
    sheet = Image.new("RGBA", (width, y + row_h + label + pad), (232, 236, 240, 255))
    d = ImageDraw.Draw(sheet)
    for code, tile, x, y in places:
        sheet.paste(tile, (x, y))
        d.text((x, y + tile.height + 3), f"{code}（{SLOTS[code][0]} × {SLOTS[code][1]}）", font=font, fill=(40, 40, 40))
    sheet.save(preview)
else:
    preview.unlink(missing_ok=True)
print(f"{len(sources)} images: kz_overlay.png, {len(singles)} single paintings, hd/, "
      + ("preview.png" if fitted else f"no preview (put images in {IMAGES.relative_to(ROOT)}/)"))
