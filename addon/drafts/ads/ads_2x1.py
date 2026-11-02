"""2 x 1 advertisements (64 x 32 px): small walls, shelves, train cars.

Slots A1-A5 in docs/ads.md. Each function returns the finished texture.
"""
from pixfont import canvas, ellipse, finish, put, rect, text

# ---------- A3 Din Tai Fung ----------
# Template: the author's reference banner (2026-11-02): dishes seen from
# above on a dark wooden table, the slogan 品嚐鼎泰豐的好味道 in white, and a
# red band with the logo in white. At 64 x 32 only the xiaolongbao steamer,
# the red band and 好味道 fit.
WOOD = (98, 62, 40)
WOOD_DARK = (80, 49, 31)
WOOD_LIGHT = (112, 73, 48)
RED = (196, 30, 36)
WHITE = (252, 250, 246)
GOLD = (248, 222, 160)
RIM = (220, 182, 124)
RIM_DARK = (178, 136, 84)
LINER = (200, 202, 204)
LINER_DOT = (184, 187, 191)
SHADOW = (160, 160, 160)
DOUGH = (253, 250, 243)
DOUGH_EDGE = (226, 216, 196)
OUTLINE = (182, 168, 142)
PLEAT = (196, 180, 152)


def wood(img, x0, y0, x1, y1):
    """Dark table boards with a faint diagonal grain."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = WOOD
            if (x + 2 * y) % 11 == 0:
                c = WOOD_DARK
            elif (x + 2 * y) % 11 == 5 and (x * 7 + y) % 3:
                c = WOOD_LIGHT
            put(img, x, y, c)


def disc(cx, cy, r):
    return [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2)
            for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r]


def xiaolongbao(img, cx, cy):
    """One dumpling from above: a cream round with an outline, a shadow on
    the paper below it, and pleats swirling into the centre."""
    body = set(disc(cx, cy, 3.4))
    for x, y in body:
        if (x + 1, y + 1) not in body:
            put(img, x + 1, y + 1, SHADOW)
    for x, y in body:
        rim = any((x + dx, y + dy) not in body for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if rim:
            put(img, x, y, OUTLINE)
        elif (x - cx) + (y - cy) > 1.5:
            put(img, x, y, DOUGH_EDGE)
        else:
            put(img, x, y, DOUGH)
    c = (round(cx), round(cy))
    for dx, dy in ((0, 0), (-1, -1), (1, 0), (0, 1), (-1, 1)):
        put(img, c[0] + dx, c[1] + dy, PLEAT if (dx, dy) != (0, 0) else OUTLINE)


def steamer_top(img, cx, cy, r):
    """A round bamboo steamer from above, lined with perforated paper."""
    for x, y in disc(cx, cy, r):
        put(img, x, y, RIM)
    for x, y in disc(cx, cy, r - 2):
        put(img, x, y, RIM_DARK)
    for x, y in disc(cx, cy, r - 3):
        put(img, x, y, LINER_DOT if (x - y) % 4 == 0 else LINER)
    for a, b in ((-3, -6), (4, -5), (-6, 1), (2, 1), (-2, 7), (6, 6)):
        xiaolongbao(img, cx + a, cy + b)


def din_tai_fung():
    img = canvas(2, 1, WOOD)
    wood(img, 0, 0, 25, 32)
    steamer_top(img, 11, 16, 13.5)
    rect(img, 25, 0, 64, 32, RED)
    text(img, 26, 3, "鼎泰豐", WHITE, 12)
    rect(img, 27, 16, 61, 17, (226, 104, 96))
    text(img, 26, 18, "好味道", GOLD, 12)
    return finish(img)


ADS = {"A3": din_tai_fung}
TITLES = {"A3": "鼎泰豐"}
