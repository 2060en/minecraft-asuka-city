"""Small drawing helpers for the advertisement textures.

Two kinds of text:
- tiny: a hand-made 3x5 pixel font (capitals, digits, a few signs) for the
  smallest Latin text, where no outline font stays readable;
- bitmap: WenQuanYi Zen Hei Sharp, an outline font that carries hand-tuned
  bitmaps at small sizes. Drawn without anti-aliasing at 9-12 px it gives
  clean kanji, kana and Latin. Text is rendered into the texture, the font
  itself is not part of the pack.
"""
from PIL import ImageDraw, ImageFont

WQY = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
_fonts = {}

TINY = {
    "A": ".#.|#.#|###|#.#|#.#", "B": "##.|#.#|##.|#.#|##.", "C": ".##|#..|#..|#..|.##",
    "D": "##.|#.#|#.#|#.#|##.", "E": "###|#..|##.|#..|###", "F": "###|#..|##.|#..|#..",
    "G": ".##|#..|#.#|#.#|.##", "H": "#.#|#.#|###|#.#|#.#", "I": "###|.#.|.#.|.#.|###",
    "J": "..#|..#|..#|#.#|.#.", "K": "#.#|#.#|##.|#.#|#.#", "L": "#..|#..|#..|#..|###",
    "M": "#.#|###|###|#.#|#.#", "N": "##.|#.#|#.#|#.#|#.#", "O": ".#.|#.#|#.#|#.#|.#.",
    "P": "##.|#.#|##.|#..|#..", "Q": ".#.|#.#|#.#|##.|.##", "R": "##.|#.#|##.|#.#|#.#",
    "S": ".##|#..|.#.|..#|##.", "T": "###|.#.|.#.|.#.|.#.", "U": "#.#|#.#|#.#|#.#|###",
    "V": "#.#|#.#|#.#|#.#|.#.", "W": "#.#|#.#|###|###|#.#", "X": "#.#|#.#|.#.|#.#|#.#",
    "Y": "#.#|#.#|.#.|.#.|.#.", "Z": "###|..#|.#.|#..|###",
    "0": "###|#.#|#.#|#.#|###", "1": ".#.|##.|.#.|.#.|###", "2": "##.|..#|.#.|#..|###",
    "3": "##.|..#|.#.|..#|##.", "4": "#.#|#.#|###|..#|..#", "5": "###|#..|##.|..#|##.",
    "6": ".##|#..|###|#.#|###", "7": "###|..#|.#.|.#.|.#.", "8": "###|#.#|###|#.#|###",
    "9": "###|#.#|###|..#|##.",
    "-": "...|...|###|...|...", ".": "...|...|...|...|.#.", "/": "..#|..#|.#.|#..|#..",
    ":": "...|.#.|...|.#.|...", "!": ".#.|.#.|.#.|...|.#.", "+": "...|.#.|###|.#.|...",
    "%": "#.#|..#|.#.|#..|#.#", "'": ".#.|.#.|...|...|...",
}


def tiny_width(s, gap=1):
    w = 0
    for ch in s:
        w += (2 if ch == " " else 3) + gap
    return max(0, w - gap)


def tiny(img, x, y, s, color, gap=1):
    """Draw s in the 3x5 font with its top-left at (x, y)."""
    px = img.load()
    for ch in s.upper():
        if ch == " ":
            x += 2 + gap
            continue
        rows = TINY[ch].split("|")
        for dy, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c == "#" and 0 <= x + dx < img.width and 0 <= y + dy < img.height:
                    px[x + dx, y + dy] = tuple(color) + (255,)
        x += 3 + gap
    return x


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(WQY, size, index=1)   # index 1: Zen Hei Sharp
    return _fonts[size]


def text_box(s, size):
    """(left, top, right, bottom) of the inked pixels of s, relative to the draw origin."""
    return font(size).getbbox(s)


def text_width(s, size):
    l, _, r, _ = text_box(s, size)
    return r - l


def text(img, x, y, s, color, size, anchor_ink=True):
    """Draw s with the bitmap font. With anchor_ink, (x, y) is the top-left of the ink."""
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    if anchor_ink:
        l, t, _, _ = text_box(s, size)
        x, y = x - l, y - t
    d.text((x, y), s, font=font(size), fill=tuple(color) + (255,))


def vtext(img, x, y, s, color, size, gap=1):
    """Vertical Japanese text, one character per line, centred on column x."""
    for ch in s:
        l, t, r, b = text_box(ch, size)
        w = r - l
        text(img, x - w // 2, y, ch, color, size)
        y += size + gap
    return y


def rect(img, x0, y0, x1, y1, color):
    """Fill [x0, x1) x [y0, y1)."""
    if x1 > x0 and y1 > y0:
        ImageDraw.Draw(img).rectangle([x0, y0, x1 - 1, y1 - 1], fill=tuple(color) + (255,))


def put(img, x, y, color):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), tuple(color) + (255,))


def vgrad(img, x0, y0, x1, y1, top, bottom):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        rect(img, x0, y, x1, y + 1, c)


def frame(img, color, width=1):
    w, h = img.size
    for i in range(width):
        rect(img, i, i, w - i, i + 1, color)
        rect(img, i, h - 1 - i, w - i, h - i, color)
        rect(img, i, i, i + 1, h - i, color)
        rect(img, w - 1 - i, i, w - i, h - i, color)
