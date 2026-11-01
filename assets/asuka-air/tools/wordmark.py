"""Build the ASUKA AIR wordmark (Syne Bold, outlined) and the logo lockups.

usage: python3 -I wordmark.py <Syne-Bold.ttf> <outdir>
Syne: https://fonts.google.com/specimen/Syne (SIL Open Font License)
"""
import math
import os
import re
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont



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


HERE = os.path.dirname(os.path.abspath(__file__))
SQUARE = os.path.join(HERE, "..", "asuka-air-symbol-square.svg")   # source of the lines (from taper.py)
LINES_BOX = (128, 275, 895, 731)          # lines + dot bbox in the 1024 artwork


def _inner(path, ink):
    sym = open(path).read()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", sym, re.S).group(1)
    inner = re.sub(r"<title>.*?</title>", "", inner)
    return inner.replace('fill="#000"', f'fill="{ink}"')


def _lines(ink):
    """lines + dot only, taken from the square artwork with its background removed."""
    inner = _inner(SQUARE, ink)
    inner = re.sub(r"<rect[^>]*/>", "", inner)
    return inner.replace('fill="#fff"', f'fill="{ink}"')


def _svg(W, H, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" '
            f'height="{H:.0f}"><title>{title}</title>{body}</svg>\n')


def build_all(fontfile, outdir, track=0.07, sym_ratio=1.5, gap_ratio=0.55):
    os.makedirs(outdir, exist_ok=True)
    paths, ww, cap = wordmark(fontfile, track=track)
    pad = 0.25 * cap

    def words(ink, dx, dy):
        return (f'<g fill="{ink}" transform="translate({dx:.2f},{dy:.2f})">'
                + "".join(f'<path d="{d}"/>' for d in paths) + "</g>")

    x0, y0, x1, y1 = LINES_BOX
    for ink, tag in (("#000", ""), ("#fff", "-white")):
        # primary: frameless symbol + wordmark, transparent background
        hs = sym_ratio * cap
        s = hs / (y1 - y0)
        sw = (x1 - x0) * s
        H = hs + 2 * pad
        W = pad + sw + gap_ratio * cap + ww + pad
        body = (f'<g transform="translate({pad - x0 * s:.2f},{pad - y0 * s:.2f}) scale({s:.5f})">'
                f'{_lines(ink)}</g>' + words(ink, pad + sw + gap_ratio * cap, pad + (hs - cap) / 2))
        open(f"{outdir}/asuka-air-logo{tag}.svg", "w").write(_svg(W, H, body, "Asuka Air"))
        # wordmark only
        m = 0.04 * cap
        open(f"{outdir}/asuka-air-wordmark{tag}.svg", "w").write(
            _svg(ww + 2 * m, cap + 2 * m, words(ink, m, m), "ASUKA AIR"))
        # symbol only (tight crop, transparent)
        m = 0.06 * (y1 - y0)
        body = (f'<g transform="translate({m - x0:.2f},{m - y0:.2f})">{_lines(ink)}</g>')
        open(f"{outdir}/asuka-air-symbol-lines{tag}.svg", "w").write(
            _svg(x1 - x0 + 2 * m, y1 - y0 + 2 * m, body, "Asuka Air symbol"))

    # secondary: circle emblem + wordmark (light backgrounds only), original proportions
    D = cap / 0.35
    s = D / 984.0
    gap = 0.23 * D
    pad = 0.1 * D
    circle = _inner(os.path.join(HERE, "..", "asuka-air-symbol-circle.svg"), "#000")
    body = (f'<g transform="translate({pad - 20 * s:.2f},{pad - 19 * s:.2f}) scale({s:.5f})">{circle}</g>'
            + words("#000", pad + D + gap, pad + D / 2 - cap / 2))
    open(f"{outdir}/asuka-air-logo-circle.svg", "w").write(
        _svg(pad + D + gap + ww + pad, D + 2 * pad, body, "Asuka Air"))


if __name__ == "__main__":
    import json
    kw = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    build_all(sys.argv[1], sys.argv[2], **kw)
