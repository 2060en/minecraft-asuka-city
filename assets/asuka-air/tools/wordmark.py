"""Build ASUKA AIR wordmark options as outlined SVG, locked up with the final circle symbol."""
import math
import re
import sys

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

import os
SYMBOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "asuka-air-symbol-circle.svg")


def glyph_path(font, ch, scale, x, base):
    gs = font.getGlyphSet()
    name = font.getBestCmap()[ord(ch)]
    pen = SVGPathPen(gs)
    tp = TransformPen(pen, (scale, 0, 0, -scale, x, base))
    gs[name].draw(tp)
    return pen.getCommands(), gs[name].width * scale


def cap_height(font):
    os2 = font["OS/2"]
    ch = getattr(os2, "sCapHeight", 0)
    if not ch:
        from fontTools.pens.boundsPen import BoundsPen
        gs = font.getGlyphSet()
        bp = BoundsPen(gs)
        gs[font.getBestCmap()[ord("H")]].draw(bp)
        ch = bp.bounds[3]
    return ch


def bounds(font, ch, scale, x, base):
    from fontTools.pens.boundsPen import BoundsPen
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[ord(ch)]].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    return x + x0 * scale, base - y1 * scale, x + x1 * scale, base - y0 * scale


def taper_stroke(x0, x1, y, half, tail_frac=0.55, head_frac=0.18, n=80):
    """horizontal streamline stroke: long thin tail at x0 (left), short point at x1 (right)."""
    L = x1 - x0
    top, bot = [], []
    for i in range(n + 1):
        s = L * i / n
        a = 1.0
        if s < L * tail_frac:
            u = s / (L * tail_frac)
            a = min(a, (u * u * (3 - 2 * u)) ** 0.6)
        if L - s < L * head_frac:
            u = (L - s) / (L * head_frac)
            a = min(a, math.sin(u * math.pi / 2) ** 0.7)
        top.append((x0 + s, y - half * a))
        bot.append((x0 + s, y + half * a))
    ring = top + bot[::-1]
    return "M" + " L".join(f"{px:.2f},{py:.2f}" for px, py in ring) + " Z"


def wordmark(fontfile, cap=126, track=0.12, swoosh=None):
    """swoosh: dict(height=frac of cap above baseline, thick=frac of cap, tail=frac of cap beyond left leg)"""
    font = TTFont(fontfile)
    upm = font["head"].unitsPerEm
    sc = cap / cap_height(font)
    em = upm * sc
    x = 0.0
    base = cap
    paths = []
    for ch in "ASUKA AIR":
        if ch == " ":
            _, adv = glyph_path(font, " ", sc, x, base)
            x += adv + track * em
            continue
        use = ch
        if swoosh and ch == "A" and 0x39B in font.getBestCmap():
            use = "Λ"
        d, adv = glyph_path(font, use, sc, x, base)
        paths.append(d)
        if swoosh and ch == "A":
            bx0, by0, bx1, by1 = bounds(font, use, sc, x, base)
            yy = base - swoosh["height"] * cap
            half = swoosh["thick"] * cap / 2
            # span: from beyond the left leg (tail) to just inside the right leg
            w = bx1 - bx0
            paths.append(taper_stroke(bx0 + w * swoosh.get("start", 0.12),
                                      bx1 + swoosh.get("over", 0.08) * cap, yy, half,
                                      tail_frac=swoosh.get("tail_frac", 0.45), head_frac=swoosh.get("head_frac", 0.22)))
        x += adv + track * em
    width = x - track * em
    return paths, width, cap


def lockup(fontfile, out, **kw):
    D = 364.0                         # circle diameter, as in the original lockup
    paths, ww, cap = wordmark(fontfile, **kw)
    sym = open(SYMBOL).read()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", sym, re.S).group(1)
    inner = re.sub(r"<title>.*?</title>", "", inner)
    pad = 38
    gap = 84
    s = D / 984.0                     # symbol svg circle r=492 -> diameter 984
    H = D + 2 * pad
    W = pad + D + gap + ww + pad + 20
    ty = pad + D / 2 - cap / 2
    body = (f'<g transform="translate({pad - 20 * s:.2f},{pad - 19 * s:.2f}) scale({s:.5f})">{inner}</g>'
            f'<g fill="#000" transform="translate({pad + D + gap:.2f},{ty:.2f})">'
            + "".join(f'<path d="{d}"/>' for d in paths) + "</g>")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">'
           f'<title>Asuka Air</title>{body}</svg>\n')
    open(out, "w").write(svg)
    # wordmark only
    wsvg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 {ww + 40:.0f} {cap + 20:.0f}" '
            f'width="{ww + 40:.0f}" height="{cap + 20:.0f}"><title>ASUKA AIR</title><g fill="#000">'
            + "".join(f'<path d="{d}"/>' for d in paths) + "</g></svg>\n")
    open(out.replace(".svg", "-wordmark.svg"), "w").write(wsvg)


if __name__ == "__main__":
    import json
    lockup(sys.argv[1], sys.argv[2], **json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
