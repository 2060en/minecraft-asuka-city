"""2 x 1 advertisements (64 x 32 px): small walls, shelves, train cars.

Slots A1-A5 in docs/ads.md. Each function returns the finished texture.
"""
from pixfont import canvas, ellipse, finish, put, rect, text

# ---------- A3 Din Tai Fung ----------
# Template: the author's reference banner (2026-11-02), kept as it is:
# dishes seen from above on a dark wooden table (xiaolongbao, beef noodle
# soup, wontons in chili oil, chicken soup, shrimp fried rice, a side dish,
# shumai), and a red band on the right with the logo written vertically in
# white. No slogan (the author asked to leave out 好味道).
WOOD = (92, 58, 38)
WOOD_DARK = (82, 51, 33)
WOOD_LIGHT = (101, 65, 43)
MAT = (158, 120, 78)
MAT_DARK = (136, 100, 62)
RED = (200, 28, 36)
WHITE = (252, 250, 246)
CHINA = (247, 246, 243)
CHINA_SHADE = (206, 204, 200)
RIM = (222, 184, 126)
RIM_DARK = (178, 136, 84)
LINER = (200, 202, 204)
LINER_DOT = (186, 189, 193)

# The logo, hand-drawn 9 x 8 with a 1-pixel gap between the characters: at
# this size the outline font turns 豐 into a solid block.
LOGO = {
    "鼎": ["..#####..",
           "..#...#..",
           "..#####..",
           "..#...#..",
           ".#######.",
           "##.#.#.##",
           ".#.#.#.#.",
           "#..#.#..#"],
    "泰": ["....#....",
           ".#######.",
           "..#####..",
           "#########",
           "..#.#.#..",
           ".#.###.#.",
           "#.#.#.#.#",
           "...##...."],
    "豐": ["..#...#..",
           "#########",
           "#.#.#.#.#",
           "#########",
           ".#######.",
           ".#.....#.",
           ".#######.",
           "#########"],
}


def wood(img, x0, y0, x1, y1):
    """Dark table boards with a soft diagonal grain, and a bamboo place mat
    running diagonally through the middle, as in the reference."""
    for y in range(y0, y1):
        for x in range(x0, x1):
            m = x + 0.55 * (y - 14)
            if 21 <= m <= 37:                       # the mat
                c = MAT_DARK if (2 * x + y) % 3 == 0 else MAT
            else:
                band = (x + 2 * y) // 3 % 5
                c = (WOOD_DARK, WOOD, WOOD, WOOD_LIGHT, WOOD)[band]
            put(img, x, y, c)


def disc(cx, cy, r):
    return [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2)
            for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r]


def bowl(img, cx, cy, r, fill):
    """A white bowl or plate from above: a china rim, shaded at the lower
    right, and fill(x, y, dx, dy) colouring the inside."""
    for x, y in disc(cx, cy, r):
        lower_right = (x - cx) + (y - cy) > r * 0.9
        put(img, x, y, CHINA_SHADE if lower_right else CHINA)
    for x, y in disc(cx, cy, r - 1.5):
        c = fill(x, y, x - cx, y - cy)
        if c:
            put(img, x, y, c)


def steamer(img, cx, cy, r, item):
    """A bamboo steamer from above, lined with paper, item(cx, cy) drawn on
    a ring of places."""
    for x, y in disc(cx, cy, r):
        put(img, x, y, RIM)
    for x, y in disc(cx, cy, r - 1.5):
        put(img, x, y, RIM_DARK)
    for x, y in disc(cx, cy, r - 2.5):
        put(img, x, y, LINER_DOT if (x - y) % 4 == 0 else LINER)
    for dx, dy in ((-3, -3), (3, -3), (-3, 3), (3, 3), (0, 0)) if r > 8 else ((-2.5, -2.5), (2.5, -2.5), (-2.5, 2.5), (2.5, 2.5)):
        item(img, cx + dx, cy + dy)


def piece(img, cx, cy, body_color, edge_color, top=None):
    """A dumpling-sized round on steamer paper: 5 px across, a darker edge on
    the lower right and a shadow beside it."""
    body = set(disc(cx, cy, 2.5))
    for x, y in body:
        if (x + 1, y + 1) not in body:
            put(img, x + 1, y + 1, (150, 150, 152))
    for x, y in body:
        outer = any((x + a, y + b) not in body for a, b in ((1, 0), (0, 1)))
        put(img, x, y, edge_color if outer else body_color)
    if top:
        top(round(cx), round(cy))


def xiaolongbao(img, cx, cy):
    def knot(x, y):
        put(img, x, y, (192, 176, 148))
        put(img, x - 1, y - 1, (222, 210, 186))
    piece(img, cx, cy, (253, 250, 243), (204, 192, 168), knot)


def shumai(img, cx, cy):
    def shrimp(x, y):
        for a, b in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
            put(img, x + a, y + b, (236, 128, 92))
    piece(img, cx, cy, (238, 222, 160), (200, 182, 120), shrimp)


def beef_noodle(x, y, dx, dy):
    if (dx, dy) in ((-2, 0), (-1, 0), (-2, 1), (2, -1), (3, -1), (2, 0), (0, 2), (1, 2)):
        return (78, 38, 22)                          # beef
    if (x * 3 + y) % 7 == 0:
        return (226, 200, 140)                       # noodles
    if (x + y * 5) % 11 == 0:
        return (96, 156, 62)                         # spring onion
    return (132, 54, 28)                             # broth


def wontons(x, y, dx, dy):
    for wx, wy in ((-2, -1), (1, -2), (2, 1), (-1, 2)):
        if abs(dx - wx) + abs(dy - wy) <= 1:
            return (242, 232, 214)
    if (x + y) % 6 == 0:
        return (96, 156, 62)
    return (178, 42, 22) if (x * 5 + y) % 4 else (214, 92, 40)


def chicken_soup(x, y, dx, dy):
    if abs(dx) + abs(dy) <= 1:
        return (246, 240, 230)
    return (232, 218, 182)


def fried_rice(x, y, dx, dy):
    if dx * dx + dy * dy > 24:
        return None                                  # plate shows round the rice
    if (x * 7 + y * 3) % 9 == 0:
        return (238, 140, 112)                       # shrimp
    if (x + y * 2) % 5 == 0:
        return (250, 206, 76)                        # egg
    if (x * 3 + y) % 13 == 0:
        return (110, 160, 70)
    return (238, 224, 176)


def side_dish(x, y, dx, dy):
    return (84, 56, 30) if (x + y) % 2 else (150, 106, 58)


def din_tai_fung():
    img = canvas(2, 1, WOOD)
    wood(img, 0, 0, 51, 32)
    steamer(img, 13, 7, 9, xiaolongbao)              # top row
    bowl(img, 28.5, 4.5, 7, beef_noodle)
    bowl(img, 42.5, 7.5, 7, wontons)
    bowl(img, 5, 21, 4.6, chicken_soup)              # bottom row
    bowl(img, 17.5, 26, 8, fried_rice)
    bowl(img, 29, 26.5, 4, side_dish)
    steamer(img, 42.5, 25.5, 8.8, shumai)
    rect(img, 51, 0, 64, 32, RED)
    for i, ch in enumerate("鼎泰豐"):
        for dy, row in enumerate(LOGO[ch]):
            for dx, c in enumerate(row):
                if c == "#":
                    put(img, 52 + dx, 3 + 9 * i + dy, WHITE)
    return finish(img)


ADS = {"A3": din_tai_fung}
TITLES = {"A3": "鼎泰豐（照作者給的橫幅）"}
