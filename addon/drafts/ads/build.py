"""Put the author's advertisement images onto the paintings.

Run from the repository root:
    python3 addon/drafts/ads/build.py [--vanilla DIR]

Resource pack only. One image per painting slot (docs/ads.md) sits in
addon/drafts/ads/images/, named by the slot code: A1.png, C4.png and so on
(png, jpg or webp). pixelate.py makes them from the author's originals, or
the author pixelates an image by hand. This script places the images as
they are: it does not draw, crop or resample them (decided 2026-11-02),
with one exception below.

- An image must have its painting's shape (w x h blocks) with a whole
  number of pixels per block; otherwise the script stops and says what
  size it expected.
- The 1.21 paintings are one file each: the image is copied as it is, as
  painting/<name>.png.
- The classic paintings share one atlas, kz.png (16 x 16 blocks), and an
  atlas has one resolution. So the atlas takes the largest pixels-per-block
  among its images (at least the vanilla 16), and an image with fewer is
  enlarged with nearest-neighbour, which keeps pixel art sharp; the script
  says so, and warns when the enlargement is not a whole number. The
  laptop parts (addon/drafts/laptop/, 16 px per block) are enlarged the same
  way and never covered: images for S1 and S2 are refused.

Outputs, in this folder:
- kz_overlay.png: the laptop parts plus every advertisement on a classic
  painting, transparent elsewhere
- painting/<name>.png: the 1.21 paintings that have an advertisement
- preview.png: every advertisement, flat, labelled with its code (enlarged
  for viewing only)

With --vanilla DIR (a folder holding the vanilla textures/painting files, for
example from https://github.com/Mojang/bedrock-samples), it also writes the
complete kz.png to addon/build/textures/painting/: vanilla enlarged to the
atlas resolution, then the overlay on top. addon/build/ is not committed, so
no vanilla image ends up in the repository.

Whether the game shows a kz.png larger than 256 x 256 and single paintings
finer than 16 px per block correctly needs a test in game.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGES = HERE / "images"
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

images, per_block = {}, {}
for code, f in sources.items():
    w, h, file, pos = SLOTS[code]
    img = Image.open(f).convert("RGBA")
    if img.width % w or img.height % h or img.width // w != img.height // h:
        raise SystemExit(f"{f.name}: {img.width} x {img.height} does not fit {code}, a {w} x {h} painting; "
                         f"it needs {w}:{h} with whole pixels per block, e.g. {w * 32} x {h * 32}")
    images[code] = img
    per_block[code] = img.width // w

atlas_codes = [c for c in images if SLOTS[c][3]]
scale = max([16] + [per_block[c] for c in atlas_codes])       # pixels per block in kz.png
laptop = Image.open(ROOT / "addon/drafts/laptop/kz_overlay.png")
overlay = laptop.resize((16 * scale, 16 * scale), Image.NEAREST)
if scale % 16:
    print(f"  kz.png at {scale} px per block: the 16 px laptop parts are enlarged by {scale / 16:g}, not a whole number")
for code in atlas_codes:
    w, h, file, (x, y) = SLOTS[code]
    img = images[code]
    if per_block[code] != scale:
        note = "" if scale % per_block[code] == 0 else " (not a whole number: pixels will be uneven)"
        print(f"  {code}: {per_block[code]} px per block, enlarged to the atlas's {scale}{note}")
        img = img.resize((w * scale, h * scale), Image.NEAREST)
    x, y = x * scale // 16, y * scale // 16
    assert not overlay.crop((x, y, x + w * scale, y + h * scale)).getbbox(), f"{code} would cover the laptop"
    overlay.paste(img, (x, y))
overlay.save(HERE / "kz_overlay.png")

singles = {SLOTS[c][2]: images[c] for c in images if not SLOTS[c][3]}
(HERE / "painting").mkdir(exist_ok=True)
for old in (HERE / "painting").glob("*.png"):
    if old.stem not in singles:
        old.unlink()
for file, img in singles.items():
    img.save(HERE / "painting" / f"{file}.png")

if args.vanilla:
    out = ROOT / "addon/build/textures/painting"
    out.mkdir(parents=True, exist_ok=True)
    full = Image.open(args.vanilla / "kz.png").convert("RGBA").resize(overlay.size, Image.NEAREST)
    full.alpha_composite(overlay)
    full.save(out / "kz.png")
    for file, img in singles.items():
        img.save(out / f"{file}.png")
    print(f"wrote {out.relative_to(ROOT)}/kz.png and {len(singles)} single paintings")

# ---------- preview: every advertisement, flat, 128 px per block for viewing ----------
preview = HERE / "preview.png"
if images:
    font = ImageFont.truetype(FONT, 16)
    tiles = [(code, img.resize((SLOTS[code][0] * 128, SLOTS[code][1] * 128), Image.NEAREST)) for code, img in images.items()]
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
print(f"{len(sources)} images: kz_overlay.png at {scale} px per block, {len(singles)} single paintings, "
      + ("preview.png" if images else f"no preview (put images in {IMAGES.relative_to(ROOT)}/)"))
