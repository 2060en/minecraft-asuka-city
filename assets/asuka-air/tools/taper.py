"""Rebuild the Asuka Air symbol (3 wind lines + dot) with tapered stroke ends.

Centerlines are traced from the original 1024px artwork, so the composition is unchanged;
only the stroke ends (and the width profile near them) differ.
usage: python3 -I taper.py <original.png> <outdir>
"""
import math
import os
import sys

import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
HALF = 21.5            # half stroke width of the original (43px)
DOT = (857.0, 313.0, 38.5)

# ---------- trace centerlines ----------
im = np.array(Image.open(SRC).convert('L')) > 128
H, W = im.shape
lab = np.zeros(im.shape, int)
n = 0
for y in range(H):
    for x in range(W):
        if im[y, x] and not lab[y, x]:
            n += 1
            st = [(y, x)]
            lab[y, x] = n
            while st:
                cy, cx = st.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = cy + dy, cx + dx
                    if 0 <= yy < H and 0 <= xx < W and im[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        st.append((yy, xx))

lines = []
for k in range(1, n + 1):
    ys, xs = np.nonzero(lab == k)
    if len(xs) < 8000:
        continue                                   # the dot
    x0, x1 = xs.min() + HALF, xs.max() - HALF       # centerline span (round caps removed)
    pts = []
    for x in range(int(math.ceil(x0)), int(x1) + 1):
        col = ys[xs == x]
        pts.append((x, (col.min() + col.max() + 1) / 2.0))
    p = np.array(pts, float)
    # smooth y (moving average) to remove pixel stair-steps
    k_ = 15
    pad = np.pad(p[:, 1], (k_ // 2, k_ // 2), mode='edge')
    p[:, 1] = np.convolve(pad, np.ones(k_) / k_, mode='valid')
    # extend straight to the original outer extents (cap tips)
    left = np.array([[p[0, 0] - HALF, p[0, 1]]])
    right = np.array([[p[-1, 0] + HALF, p[-1, 1]]])
    p = np.vstack([left, p, right])
    lines.append(p)
lines.sort(key=lambda a: a[0, 1])                   # top -> bottom
print("lines:", [(round(l[0, 0]), round(l[-1, 0])) for l in lines])


def resample(p, step=3.0):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    s = np.arange(0, d[-1], step)
    s = np.r_[s, d[-1]]
    return np.c_[np.interp(s, d, p[:, 0]), np.interp(s, d, p[:, 1])], s


def outline(p, prof):
    q, s = resample(p)
    L = s[-1]
    t = np.gradient(q, axis=0)
    t /= np.hypot(t[:, 0], t[:, 1])[:, None]
    nrm = np.c_[-t[:, 1], t[:, 0]]
    w = np.array([prof(si, L) for si in s]) * HALF
    a = q + nrm * w[:, None]
    b = q - nrm * w[:, None]
    ring = np.vstack([a, b[::-1]])
    return ring


def smooth01(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# ---------- width profiles ----------
def prof_streamline(s, L, tail=170.0, head=72.0):
    """long hairline tail at the start, short pointed (ogive) head at the end."""
    a = 1.0
    if s < tail:
        u = s / tail
        a = min(a, smooth01(u) ** 0.6)
    if L - s < head:
        u = (L - s) / head
        a = min(a, math.sin(u * math.pi / 2) ** 0.7)
    return a


def prof_leaf(s, L, end=110.0):
    """both ends taper the same way: a sharp, symmetric leaf-like stroke."""
    a = 1.0
    for d in (s, L - s):
        if d < end:
            a = min(a, math.sin(d / end * math.pi / 2))
    return a


def d_of(ring):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ring) + " Z"


def symbol_paths(prof):
    return "".join(f'<path d="{d_of(outline(p, prof))}"/>' for p in lines) + \
        f'<circle cx="{DOT[0]}" cy="{DOT[1]}" r="{DOT[2]}"/>'


def svg(prof, bg, ink, frame):
    if frame == "square":
        back = f'<rect width="1024" height="1024" fill="{bg}"/>'
    elif frame == "circle":
        back = f'<circle cx="512" cy="511" r="492" fill="{bg}"/>'
    else:
        back = ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
            f'<title>Asuka Air symbol</title>{back}<g fill="{ink}">{symbol_paths(prof)}</g></svg>\n')


for name, prof in (("a", prof_streamline), ("b", prof_leaf)):
    open(f"{OUT}/symbol-{name}-square.svg", "w").write(svg(prof, "#000", "#fff", "square"))
    open(f"{OUT}/symbol-{name}-circle.svg", "w").write(svg(prof, "#000", "#fff", "circle"))
    open(f"{OUT}/symbol-{name}-lines.svg", "w").write(svg(prof, None, "#000", None))
print("done")
