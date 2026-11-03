"""Turn the author's original advertisement images into painting textures.

Run from the repository root:
    python3 addon/drafts/ads/pixelate.py --res 128          # writes images/
    python3 addon/drafts/ads/pixelate.py --res 256 --out DIR

Only a program step, nothing is redrawn (the author's rule, 2026-11-02):

1. crop: the original is cut to the painting's shape (w x h blocks), around
   its centre, or around "focus" from originals.json when the centre is
   the wrong place;
2. pixelate: it is shrunk to res pixels per block, each new pixel being the
   average colour of the patch of the original it covers (box filter). In
   the game a texture pixel is drawn as a sharp square, which gives the
   pixel look;
3. optional --colors N: the colours are reduced to a palette of N (no
   dithering), for a flatter pixel-art look.

originals.json maps each slot code to an image in originals/:
    "A1": {"file": "MacDonald.jpg"}
    "D5": {"file": "...", "focus": [0.5, 0.3]}   # crop centre, 0-1 of width and height
The output, images/<code>.png, is what build.py places on the paintings.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
ORIGINALS = HERE / "originals"

# painting size in blocks, per slot code (docs/ads.md)
SIZES = {}
for codes, size in (("A1 A2 A3 A4 A5", (2, 1)), ("B1 B2 B3", (1, 2)), ("C1 C2 C3 C4 C5 C6 C7 C8", (2, 2)),
                    ("X1 X2 X3 X4", (2, 2)), ("D1 D2 D3 D4 D5 D6 D7 D8", (3, 3)), ("E1 E2 E3 E4 E5", (4, 2)),
                    ("F1 F2", (3, 4)), ("G1 G2", (4, 3)), ("H1 H2 H3 H4 H5", (4, 4)),
                    ("S3 S4 S5 S6 S7 S8", (1, 1))):
    for c in codes.split():
        SIZES[c] = size


def crop_to(img, w, h, focus=(0.5, 0.5)):
    """The largest w:h window of img, centred on focus as far as it can."""
    W, H = img.size
    if W * h > H * w:                        # wider than the painting
        nw = round(H * w / h)
        x0 = min(max(round(focus[0] * W - nw / 2), 0), W - nw)
        return img.crop((x0, 0, x0 + nw, H))
    nh = round(W * h / w)
    y0 = min(max(round(focus[1] * H - nh / 2), 0), H - nh)
    return img.crop((0, y0, W, y0 + nh))


def pixelate(img, w, h, res, colors=None, focus=(0.5, 0.5)):
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = crop_to(img, w, h, focus)
    small = img.resize((w * res, h * res), Image.BOX)
    if colors:
        small = small.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    return small, img.size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--res", type=int, required=True, help="pixels per block, e.g. 128 or 256")
    parser.add_argument("--colors", type=int, help="reduce to this many colours (optional)")
    parser.add_argument("--out", type=Path, default=HERE / "images", help="output folder (default images/)")
    parser.add_argument("--only", nargs="*", help="slot codes to do (default all in originals.json)")
    args = parser.parse_args()

    table = json.loads((HERE / "originals.json").read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    for code, entry in table.items():
        if code.startswith("_") or (args.only and code not in args.only):
            continue
        w, h = SIZES[code]
        src = ORIGINALS / entry["file"]
        out, cropped = pixelate(Image.open(src), w, h, args.res, args.colors, tuple(entry.get("focus", (0.5, 0.5))))
        note = ""
        if cropped[0] < w * args.res:
            note = f"  (the original is only {cropped[0]} px wide here: it is enlarged, not reduced)"
        out.save(args.out / f"{code}.png")
        print(f"{code}: {entry['file']} -> {out.width} x {out.height}{note}")


if __name__ == "__main__":
    main()
