"""Asuka Air's mark in pixels.

The brand design is in docs/world/flight-schedule.md, section 品牌設計
(branch claude/awesome-gauss-z398qi, assets/asuka-air-logo/mark.svg): black
and white like Air New Zealand, with the koru replaced by the Kuroshio. The
mark is a black disc with three white parallel flow lines, an S made of
concentric arcs, and a white dot at the end of the top line for the island.

This module redraws mark.svg from its geometry at a given diameter, without
anti-aliasing, so it stays crisp on a 32x painting.
"""
import math

from PIL import Image, ImageDraw

BLACK = (12, 12, 12)
WHITE = (250, 250, 248)

# mark.svg, viewBox 200 x 200. The flow lines and the dot sit in a group
# transformed by translate(100,100) scale(1.05) translate(-103.9,-100).
DISC = (100, 100, 96)
DOT = (168.2, 63.1, 7.2)
STROKE = 8
LINES = [
    [("M", 48.51, 94.93), ("L", 58.51, 94.93), ("A", 41, 0, 0, 85.95, 84.39),
     ("A", 83, 0, 1, 141.49, 63.07), ("L", 147.49, 63.07)],
    [("M", 36.51, 115.93), ("L", 58.51, 115.93), ("A", 62, 0, 0, 100.00, 100.00),
     ("A", 62, 0, 1, 141.49, 84.07), ("L", 165.49, 84.07)],
    [("M", 52.51, 136.93), ("L", 58.51, 136.93), ("A", 83, 0, 0, 114.05, 115.61),
     ("A", 41, 0, 1, 141.49, 105.07), ("L", 151.49, 105.07)],
]


def _group(x, y):
    return 100 + 1.05 * (x - 103.9), 100 + 1.05 * (y - 100)


def _arc(p1, p2, r, large, sweep, steps=24):
    """Points along an SVG circular arc (endpoint parameterisation)."""
    (x1, y1), (x2, y2) = p1, p2
    hx, hy = (x1 - x2) / 2, (y1 - y2) / 2
    d2 = hx * hx + hy * hy
    r = max(r, math.sqrt(d2))
    coef = math.sqrt(max(0.0, (r * r - d2) / d2))
    if large == sweep:
        coef = -coef
    cx, cy = coef * hy + (x1 + x2) / 2, -coef * hx + (y1 + y2) / 2
    a1 = math.atan2(y1 - cy, x1 - cx)
    a2 = math.atan2(y2 - cy, x2 - cx)
    da = a2 - a1
    if sweep and da < 0:
        da += 2 * math.pi
    if not sweep and da > 0:
        da -= 2 * math.pi
    return [(cx + r * math.cos(a1 + da * t / steps), cy + r * math.sin(a1 + da * t / steps)) for t in range(1, steps + 1)]


def _polyline(cmds):
    pts = []
    for c in cmds:
        if c[0] in "ML":
            pts.append((c[1], c[2]))
        else:
            _, r, large, sweep, x, y = c
            pts += _arc(pts[-1], (x, y), r, large, sweep)
    return [_group(x, y) for x, y in pts]


def mark(diameter, disc=BLACK, ink=WHITE, width=None):
    """The mark as an RGBA image, diameter x diameter pixels."""
    img = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = diameter / 192                                   # disc radius 96 -> diameter / 2
    tr = lambda x, y: ((x - 4) * s - 0.5, (y - 4) * s - 0.5)
    d.ellipse([0, 0, diameter - 1, diameter - 1], fill=disc + (255,))
    w = width or max(1, round(STROKE * 1.05 * s))
    for cmds in LINES:
        pts = [tr(x, y) for x, y in _polyline(cmds)]
        d.line([(round(x), round(y)) for x, y in pts], fill=ink + (255,), width=w, joint="curve")
    gx, gy = _group(DOT[0], DOT[1])
    cx, cy = tr(gx, gy)
    rr = max(w / 2 + 0.3, DOT[2] * 1.05 * s)
    dot = Image.new("1", img.size, 0)
    ImageDraw.Draw(dot).ellipse([round(cx - rr), round(cy - rr), round(cx + rr) - 1 + (w % 2 == 0),
                                 round(cy + rr) - 1 + (w % 2 == 0)], fill=1)
    dots = [p for p in ((x, y) for y in range(diameter) for x in range(diameter)) if dot.getpixel(p)]
    px = img.load()
    lines = {(x, y) for y in range(diameter) for x in range(diameter) if px[x, y][:3] == ink}

    # At small sizes the island dot can merge into the top line: shorten the
    # line where it touches the dot, so a 1-pixel gap shows.
    dotset = set(dots)
    for x, y in lines - dotset:
        if any((x + dx, y + dy) in dotset for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            px[x, y] = disc + (255,)
    for x, y in dots:
        px[x, y] = ink + (255,)
    return img
