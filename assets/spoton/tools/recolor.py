"""Swap the background colour of a logo image, keeping anti-aliasing and fades.

usage: python3 -I recolor.py <in> <out.png> [old_hex] [new_hex]

Each pixel is treated as a mix of a foreground colour and the old background
("colour to alpha"): alpha is how far the pixel is from the background, and
the new pixel is pixel + (1 - alpha) * (new_bg - old_bg). Solid white or mint
stays as it is, the background becomes the new colour, and soft edges and the
fading signal arcs blend into the new background the same way they did into
the old one. Pixels that differ from the background by only compression
noise are snapped to the new background.

Defaults: old #300A59 (the original deep purple), new #641F9C (purple concrete).
"""
import sys

import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
old_hex = sys.argv[3] if len(sys.argv) > 3 else "300A59"
new_hex = sys.argv[4] if len(sys.argv) > 4 else "641F9C"
old = np.array([int(old_hex[i:i + 2], 16) for i in (0, 2, 4)], float)
new = np.array([int(new_hex[i:i + 2], 16) for i in (0, 2, 4)], float)

p = np.asarray(Image.open(src).convert("RGB")).astype(float)
up = np.where(p > old, (p - old) / np.maximum(255 - old, 1), 0)
# nothing in the logo is darker than the background, so darker pixels are only noise;
# measure them on the full 0-255 scale, or a dark channel (green is about 10) would blow
# a few levels of noise up into visible blotches
down = np.where(p < old, (old - p) / 255, 0)
alpha = np.maximum(up, down).max(axis=2)

NOISE = 0.08                     # compression noise in the flat background
a = np.clip((alpha - NOISE) / (1 - NOISE), 0, 1)
res = p + (1 - a)[..., None] * (new - old)
res[a == 0] = new
Image.fromarray(np.clip(np.rint(res), 0, 255).astype(np.uint8)).save(out)
print(f"saved {out}  background pixels snapped: {(a == 0).mean():.1%}")
