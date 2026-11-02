"""2 x 1 advertisements: small walls, shelves, train cars.

Slots A1-A5 in docs/ads.md. Each function takes k (1: the 64 x 32 texture
the game uses, 2: the 128 x 64 spare) and returns the finished image.
"""
import math

from pixfont import canvas, finish, put, rect, text

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
SHADOW = (150, 150, 152)
ONION = (96, 156, 62)

# The 32x logo, hand-drawn 9 x 8 with a 1-pixel gap between the characters:
# at this size the outline font turns 豐 into a solid block. 鼎 has the two
# outer strokes beside 目 the author asked for (2026-11-02).
LOGO = {
    "鼎": ["..#####..",
           "..#...#..",
           "#.#####.#",
           "#.#...#.#",
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


def disc(cx, cy, r):
    return [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2)
            for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r]


def wood(img, x1, k):
    """Dark table boards with a soft diagonal grain, and a bamboo place mat
    running diagonally through the middle, as in the reference."""
    for y in range(img.height):
        for x in range(x1):
            m = x / k + 0.55 * (y / k - 14)
            if 21 <= m <= 37:                       # the mat
                c = MAT_DARK if (2 * x + y) % 3 == 0 else MAT
            else:
                c = (WOOD_DARK, WOOD, WOOD, WOOD_LIGHT, WOOD)[(x + 2 * y) // (3 * k) % 5]
            put(img, x, y, c)


def bowl(img, cx, cy, r, fill, k):
    """A white bowl or plate from above: a china rim, shaded at the lower
    right, and fill(x, y, u, v, k) colouring the inside, where (u, v) is the
    offset from the centre in 32x pixels."""
    cx, cy, r = cx * k, cy * k, r * k
    for x, y in disc(cx, cy, r):
        lower_right = (x - cx) + (y - cy) > r * 0.9
        put(img, x, y, CHINA_SHADE if lower_right else CHINA)
    for x, y in disc(cx, cy, r - 1.5 * k):
        c = fill(x, y, (x - cx) / k, (y - cy) / k, k)
        if c:
            put(img, x, y, c)


def steamer(img, cx, cy, r, item, k):
    """A bamboo steamer from above, lined with paper, item(cx, cy, k) drawn
    on five places (four on the small one)."""
    places = ((-3, -3), (3, -3), (-3, 3), (3, 3), (0, 0)) if r > 8 else ((-2.5, -2.5), (2.5, -2.5), (-2.5, 2.5), (2.5, 2.5))
    cx, cy = cx * k, cy * k
    for x, y in disc(cx, cy, r * k):
        put(img, x, y, RIM)
    for x, y in disc(cx, cy, (r - 1.5) * k):
        put(img, x, y, RIM_DARK)
    for x, y in disc(cx, cy, (r - 2.5) * k):
        put(img, x, y, LINER_DOT if (x - y) % 4 == 0 else LINER)
    for dx, dy in places:
        item(img, cx + dx * k, cy + dy * k, k)


def piece(img, cx, cy, k, body_color, edge_color):
    """A dumpling-sized round on steamer paper, 5 px across at 32x, darker on
    the lower-right edge, with a shadow beside it."""
    r = 2.5 * k
    body = set(disc(cx, cy, r))
    for x, y in body:
        if (x + k, y + k) not in body:
            for i in range(1, k + 1):
                put(img, x + i, y + i, SHADOW)
    for x, y in body:
        outer = (x + 1, y) not in body or (x, y + 1) not in body
        if k > 1:                                    # a wider shaded rim
            u, v = x - cx, y - cy
            outer = outer or (u * u + v * v > (r - 1.3) ** 2 and u + v > 0)
        put(img, x, y, edge_color if outer else body_color)


def xiaolongbao(img, cx, cy, k):
    piece(img, cx, cy, k, (253, 250, 243), (204, 192, 168))
    x, y = round(cx), round(cy)
    if k == 1:
        put(img, x, y, (192, 176, 148))
        put(img, x - 1, y - 1, (222, 210, 186))
    else:                                            # pleats swirling to the knot
        for a in range(8):
            t = a * math.pi / 4
            for d in (1.4, 2.2):
                put(img, round(cx + d * math.cos(t + d * 0.6)), round(cy + d * math.sin(t + d * 0.6)), (216, 204, 180))
        put(img, x, y, (186, 170, 142))
        put(img, x - 1, y, (204, 190, 164))


def shumai(img, cx, cy, k):
    piece(img, cx, cy, k, (238, 222, 160), (200, 182, 120))
    x, y = round(cx), round(cy)
    if k == 1:
        for a, b in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
            put(img, x + a, y + b, (236, 128, 92))   # shrimp on top
    else:
        for px, py in disc(cx - 0.5, cy - 0.5, 2.1):
            put(img, px, py, (236, 128, 92))
        put(img, x - 1, y - 2, (250, 176, 140))


def beef_noodle(x, y, u, v, k):
    if k == 1:
        beef = (u, v) in ((-2, 0), (-1, 0), (-2, 1), (2, -1), (3, -1), (2, 0), (0, 2), (1, 2))
    else:
        beef = any(abs(u - bu) <= 1.2 and abs(v - bv) <= 0.8 for bu, bv in ((-1.5, 0.5), (2.5, -0.5), (0.5, 2.5)))
    if beef:
        return (78, 38, 22) if (x + y) % 5 else (98, 52, 30)
    if (x * 3 + y) % 7 == 0:
        return (226, 200, 140)                       # noodles
    if (x + y * 5) % 11 == 0:
        return ONION
    return (132, 54, 28)                             # broth


def wontons(x, y, u, v, k):
    for wu, wv in ((-2, -1), (1, -2), (2, 1), (-1, 2)):
        if abs(u - wu) + abs(v - wv) <= 1:
            return (242, 232, 214) if k == 1 or abs(u - wu) + abs(v - wv) < 0.7 else (224, 210, 188)
    if (x + y) % 6 == 0 if k == 1 else (x * 7 + y * 13) % 17 == 0:
        return ONION
    return (178, 42, 22) if (x * 5 + y) % 4 else (214, 92, 40)


def chicken_soup(x, y, u, v, k):
    if abs(u) + abs(v) <= 1:
        return (246, 240, 230)
    return (232, 218, 182)


def fried_rice(x, y, u, v, k):
    if u * u + v * v > 24:
        return None                                  # plate shows round the rice
    if (x * 7 + y * 3) % 9 == 0:
        return (238, 140, 112)                       # shrimp
    if (x + y * 2) % 5 == 0:
        return (250, 206, 76)                        # egg
    if (x * 3 + y) % 13 == 0:
        return (110, 160, 70)
    return (238, 224, 176)


def side_dish(x, y, u, v, k):
    return (84, 56, 30) if (x + y) % 2 else (150, 106, 58)


def logo(img, k):
    """鼎泰豐 written vertically in white inside the red band."""
    if k == 1:
        for i, ch in enumerate("鼎泰豐"):
            for dy, row in enumerate(LOGO[ch]):
                for dx, c in enumerate(row):
                    if c == "#":
                        put(img, 52 + dx, 3 + 9 * i + dy, WHITE)
    else:                                            # the outline font, strokes doubled
        for i, ch in enumerate("鼎泰豐"):
            for off in (0, 1):
                text(img, 105 + off, 5 + 19 * i, ch, WHITE, 16)


def din_tai_fung(k=1):
    img = canvas(2, 1, WOOD, k)
    wood(img, 51 * k, k)
    steamer(img, 13, 7, 9, xiaolongbao, k)           # top row
    bowl(img, 28.5, 4.5, 7, beef_noodle, k)
    bowl(img, 42.5, 7.5, 7, wontons, k)
    bowl(img, 5, 21, 4.6, chicken_soup, k)           # bottom row
    bowl(img, 17.5, 26, 8, fried_rice, k)
    bowl(img, 29, 26.5, 4, side_dish, k)
    steamer(img, 42.5, 25.5, 8.8, shumai, k)
    rect(img, 51 * k, 0, 64 * k, 32 * k, RED)
    logo(img, k)
    return finish(img, k)


ADS = {"A3": din_tai_fung}
TITLES = {"A3": "鼎泰豐（照作者給的橫幅）"}
