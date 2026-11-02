"""2 x 1 advertisements: small walls, shelves, train cars.

Slots A1-A5 in docs/ads.md. Each function takes k (1: the 64 x 32 texture
the game uses, 2: the 128 x 64 spare) and returns the finished image.
"""
import math

from PIL import Image, ImageDraw

from pixfont import canvas, finish, put, rect, text, text_box, tiny

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


# ---------- A1 McDonald's ----------
# Template: the author's reference photo (2026-11-02), kept as it is: a dark
# grey wall and a glossy black table with reflections; behind, from the left,
# a white cup, two dark grey Signature burger boxes with gold lines and a
# gold M, an upright red fries carton and another white cup; in front, a red
# fries carton lying on its side, and a slate with a beef burger and a crispy
# chicken burger. Coordinates are in 32x pixels and scaled by k.
WALL_TOP = (62, 62, 62)
WALL_LOW = (36, 36, 37)
TABLE = (14, 14, 16)
HORIZON = 18.5
CUP = (238, 232, 222)
CUP_SHADE = (210, 204, 194)
LID = (226, 226, 224)
DOT = (232, 150, 64)
MC_RED = (212, 32, 32)
MC_RED_DARK = (168, 24, 26)
GOLD = (255, 196, 30)
BOX = (70, 68, 64)
BOX_TOP = (84, 82, 77)
BOX_LINE = (170, 136, 80)
FRY = (242, 200, 92)
FRY_LIGHT = (252, 222, 128)
FRY_DARK = (214, 160, 64)
SLATE = (56, 58, 62)
SLATE_DARK = (40, 41, 45)
SLATE_LIGHT = (70, 72, 77)
BUN = (196, 110, 46)
BUN_LIGHT = (224, 150, 78)
BUN_DARK = (160, 84, 34)
SAUCE = (240, 236, 222)
PATTY = (98, 64, 46)
CRUST = (224, 164, 82)
CRUST_LIGHT = (242, 198, 118)
TOMATO = (200, 48, 38)
LETTUCE = (96, 168, 54)
LETTUCE_DARK = (58, 120, 34)


def mask(img, draw):
    """Pixels covered by a shape drawn with ImageDraw on a blank mask."""
    m = Image.new("1", img.size, 0)
    draw(ImageDraw.Draw(m))
    return [(x, y) for y in range(img.height) for x in range(img.width) if m.getpixel((x, y))]


def poly(img, pts, k, color):
    """Fill a polygon given in 32x units; color is a colour or f(x, y)."""
    pix = mask(img, lambda d: d.polygon([(round(x * k), round(y * k)) for x, y in pts], fill=1))
    for x, y in pix:
        c = color(x, y) if callable(color) else color
        if c:
            put(img, x, y, c)
    return pix


def oval(img, x0, y0, x1, y1, k, color):
    pix = mask(img, lambda d: d.ellipse([round(x0 * k), round(y0 * k), round(x1 * k) - 1, round(y1 * k) - 1], fill=1))
    for x, y in pix:
        c = color(x, y) if callable(color) else color
        if c:
            put(img, x, y, c)
    return pix


def sprite(img, x, y, rows, color):
    for dy, row in enumerate(rows):
        for dx, c in enumerate(row):
            if c == "#":
                put(img, x + dx, y + dy, color)


# The golden arches, hand-drawn per size.
ARCHES = {
    (5, 3): [".#.#.",
             "#.#.#",
             "#...#"],
    (7, 5): [".##.##.",
             "#..#..#",
             "#..#..#",
             "#.....#",
             "#.....#"],
    (10, 6): [".##....##.",
              "#..#..#..#",
              "#...##...#",
              "#........#",
              "#........#",
              "#........#"],
    (14, 10): ["..##....##..",
               ".####..####.",
               "##..####..##",
               "##...##...##",
               "##........##",
               "##........##",
               "##........##",
               "##........##",
               "##........##",
               "##........##"],
}


def arches(img, cx, top, size, color):
    rows = ARCHES[size]
    sprite(img, round(cx - len(rows[0]) / 2), round(top), rows, color)


def cup(img, x0, x1, top, bottom, k, mark_at):
    """A white paper cup with a lid, sprinkled with orange dots, and the
    small red square with the M."""
    poly(img, [(x0, top + 1), (x1, top + 1), (x1 - 0.6, bottom), (x0 + 0.6, bottom)], k,
         lambda x, y: DOT if (x * 7 + y * 5) % (11 * k) == 0 and (x + y) % 2 == 0 else (CUP_SHADE if x > (x1 - 1.2) * k else CUP))
    rect(img, round((x0 - 0.3) * k), round(top * k), round((x1 + 0.3) * k), round((top + 1.2) * k), LID)
    rect(img, round((x0 - 0.3) * k), round((top + 1.2) * k), round((x1 + 0.3) * k), round((top + 1.2) * k) + 1, CUP_SHADE)
    mx, my = mark_at
    n = 3 if k == 1 else 6
    rect(img, round(mx * k) - n // 2, round(my * k) - n // 2, round(mx * k) - n // 2 + n, round(my * k) - n // 2 + n, MC_RED)
    if k == 1:
        put(img, round(mx), round(my) - 1 + 1, GOLD)
    else:
        arches(img, mx * k, my * k - 1, (5, 3), GOLD)


def burger_box(img, x0, x1, top, bottom, k):
    """A dark grey clamshell box seen from the front: the lid's top face, the
    front face with the word SIGNATURE (a faint light line at this size),
    large gold diamond lines and a gold M near the bottom."""
    mid = top + (bottom - top) * 0.32
    poly(img, [(x0 + 1, top), (x1 - 1, top), (x1, mid), (x0, mid)], k, BOX_TOP)
    w = x1 - x0
    period = w / 2 * k

    def face(x, y):
        u = x - x0 * k
        v = y - mid * k
        on_line = min((u - v) % period, (u + v) % period) < (1 if k == 1 else 1.4)
        if on_line and y < (bottom - 3.6) * k:
            return BOX_LINE
        return BOX

    poly(img, [(x0, mid), (x1, mid), (x1 - 0.3, bottom), (x0 + 0.3, bottom)], k, face)
    sig_y = round((mid + 1.2) * k)
    for x in range(round((x0 + w * 0.3) * k), round((x1 - w * 0.3) * k)):
        if k == 1 or x % 3:
            put(img, x, sig_y, (150, 146, 138))
    rect(img, round(x0 * k), round((bottom - 0.6) * k), round(x1 * k), round(bottom * k), (150, 104, 48))
    arches(img, (x0 + x1) / 2 * k, (bottom - 3.4) * k, (5, 3) if k == 1 else (10, 6), GOLD)


def fries(img, x0, x1, y0, y1, k, lying=False):
    """Golden fries: sticks of three shades, upright or lying."""
    for x in range(round(x0 * k), round(x1 * k)):
        for y in range(round(y0 * k), round(y1 * k)):
            if lying:
                tone = (y // max(1, k) * 3 + x // (4 * k)) % 4
            else:
                tone = (x // max(1, k) * 5 + y // (5 * k)) % 4
            if (x * 3 + y * 7) % (13 if k == 1 else 9) == 0:
                continue                             # gaps between the sticks
            put(img, x, y, (FRY, FRY_LIGHT, FRY_DARK, FRY)[tone])


def band(img, x0, x1, y0, y1, k, color):
    """A horizontal band in 32x units, at least one pixel tall."""
    Y0 = math.floor(y0 * k + 0.5)
    Y1 = max(Y0 + 1, math.floor(y1 * k + 0.5))
    rect(img, math.floor(x0 * k + 0.5), Y0, math.floor(x1 * k + 0.5), Y1, color)


def burger(img, x0, x1, top, k, chicken):
    """A burger seen from the front, a little above. From the top: the domed
    bun, white sauce, the patty (or a crispy fillet wider than the bun),
    tomato, frilly lettuce wider than the bun, and the bottom bun."""
    w = x1 - x0
    bx0, bx1 = (x0 + w * 0.12, x1 - w * 0.14) if chicken else (x0 + w * 0.08, x1 - w * 0.06)
    poly(img, [(bx0 + 0.3, top + 6.2), (bx1 - 0.3, top + 6.2), (bx1 - 0.8, top + 7.6), (bx0 + 0.8, top + 7.6)], k, BUN_DARK)
    for x in range(round(x0 * k), round(x1 * k)):
        h = 1.3 + 0.5 * math.sin(x / k * 2.1) + 0.4 * math.sin(x / k * 5.3)
        for y in range(math.floor((top + 5.2) * k + 0.5), math.floor((top + 5.2 + h) * k + 0.5) + 1):
            put(img, x, y, LETTUCE if (x + 2 * y) % 4 else LETTUCE_DARK)
    band(img, bx0 + 0.6, bx1 - 0.6, top + 4.9, top + 5.3, k, TOMATO)
    if chicken:
        poly(img, [(x0 + 0.4, top + 3.2), (x1 - 0.6, top + 3.3), (x1, top + 5), (x0, top + 4.9)], k,
             lambda x, y: CRUST_LIGHT if (x * 5 + y * 3) % 4 == 0 else CRUST)
    else:
        band(img, bx0, bx1 + 0.4, top + 3.6, top + 4.9, k, PATTY)
    band(img, bx0 + 0.8, bx1 - 0.8, top + 3.0, top + 3.6, k, SAUCE)
    oval(img, bx0, top, bx1, top + 5.4, k,
         lambda x, y: None if y >= (top + 2.7) * k else
         (BUN_LIGHT if (x - bx0 * k) < (bx1 - bx0) * k * 0.45 and y < (top + 1.3) * k else BUN))
    if k > 1:                                        # the cross cut on the bun
        cx = round((bx0 + bx1) / 2 * k)
        for i in range(-4, 5):
            put(img, cx + i, round((top + 1.4) * k) + abs(i) // 4, BUN_DARK)


def mcdonalds(k=1):
    img = canvas(2, 1, WALL_LOW, k)
    W, H = img.size
    for y in range(round(HORIZON * k)):              # the wall, lighter at the top middle
        for x in range(W):
            t = y / (HORIZON * k)
            c = tuple(round(a + (b - a) * t) for a, b in zip(WALL_TOP, WALL_LOW))
            dx = abs(x - W / 2) / (W / 2)
            put(img, x, y, tuple(max(0, round(v - 14 * dx)) for v in c))
    rect(img, 0, round(HORIZON * k), W, H, TABLE)

    back = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cup(back, 7.4, 14.9, 6.6, 18.5, k, (10.7, 14))
    burger_box(back, 14.6, 27.8, 9.6, 18.2, k)
    burger_box(back, 28.4, 41, 10, 18.4, k)
    cup(back, 48.8, 57.2, 6.2, 19.6, k, (52.2, 11.5))
    fries(back, 40.6, 49.8, 10.4, 13.6, k)
    poly(back, [(40.2, 12.8), (50.2, 12.6), (49.6, 20.8), (40.8, 21)], k,
         lambda x, y: MC_RED_DARK if x > 48.6 * k else MC_RED)
    arches(back, 45.2 * k, 15 * k, (7, 5) if k == 1 else (14, 10), GOLD)

    front = Image.new("RGBA", img.size, (0, 0, 0, 0))
    # the carton lying on its side, opening to the right, fries spilling out
    poly(front, [(4.4, 16.6), (11.2, 14.4), (12.4, 20.6), (5.2, 21.6)], k, MC_RED)
    poly(front, [(4.4, 16.6), (5.2, 21.6), (5.9, 21.5), (5.1, 16.4)], k, MC_RED_DARK)
    fries(front, 10.4, 16.4, 15, 20.4, k, lying=True)
    side = [row[::-1] for row in zip(*ARCHES[(5, 3) if k == 1 else (10, 6)])]   # the M, turned on its side
    sprite(front, round(7.2 * k), round(16.8 * k), ["".join(r) for r in side], GOLD)
    # the slate
    poly(front, [(6.6, 25.4), (39.8, 27.2), (39.8, 27.9), (6.6, 26.1)], k, SLATE_DARK)
    poly(front, [(12.2, 22.6), (45.4, 22), (39.8, 27.2), (6.6, 25.4)], k,
         lambda x, y: SLATE_LIGHT if (x * 3 + y * 7) % 11 == 0 else (SLATE_DARK if (x + y * 5) % 13 == 0 else SLATE))
    burger(front, 12, 25.4, 17.8, k, chicken=False)
    burger(front, 24.6, 41.6, 17.2, k, chicken=True)

    # reflections on the glossy table
    def reflect(layer, base):
        flipped = layer.transpose(Image.FLIP_TOP_BOTTOM)
        shift = round(2 * base * k) - img.height
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.paste(flipped, (0, shift))
        px = out.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if a and y >= base * k:
                    f = 0.5 - 0.25 * (y - base * k) / (img.height - base * k + 1)
                    px[x, y] = (round(r * f + TABLE[0] * (1 - f)), round(g * f + TABLE[1] * (1 - f)),
                                round(b * f + TABLE[2] * (1 - f)), 255)
                else:
                    px[x, y] = (0, 0, 0, 0)
        return out

    img.alpha_composite(reflect(back, 21))
    img.alpha_composite(back)
    img.alpha_composite(reflect(front, 28))
    img.alpha_composite(front)
    return finish(img, k)


# ---------- A4 coffee (unbranded) ----------
# Template: the author's reference photo (2026-11-02): a dark wall and a grey
# concrete table; behind, a tall iced black coffee; in front, an iced latte
# with espresso being poured in from a small glass jug by a hand coming in
# from the top right; a white milk jug at the lower left, coffee beans on
# the table, and the name in white, wide-spaced capitals at the bottom. The
# photo is about 4:3, so the scene keeps its proportions in the middle and
# the wall, the table and the arm run on to the sides. Unbranded: the name
# becomes a coffee-bean mark and COFFEE.
C_WALL = (34, 36, 39)
C_WALL2 = (41, 43, 46)
C_TABLE = (122, 124, 127)
C_TABLE_D = (114, 116, 119)
C_TABLE_L = (130, 132, 135)
C_GLASS = (188, 194, 198)
C_BLACK = (54, 27, 16)
C_BLACK_LOW = (98, 45, 22)
C_BLACK_GLOW = (132, 62, 28)
C_ICE = (214, 216, 218)
C_ICE_D = (178, 182, 186)
C_ESPRESSO = (150, 84, 40)
C_TAN = (204, 148, 96)
C_CREAM = (234, 214, 186)
C_MILK = (243, 241, 235)
C_MILK_D = (220, 218, 212)
C_SKIN = (234, 196, 166)
C_SKIN_D = (206, 162, 130)
C_AMBER = (186, 98, 40)
C_AMBER_L = (228, 158, 88)
C_CHINA = (245, 245, 243)
C_CHINA_D = (212, 212, 210)
C_BEAN = (74, 42, 24)
C_BEAN_D = (40, 22, 14)
C_TEXT = (247, 247, 245)

SC = 25 / 376                    # 32x pixels per pixel of the reference photo
SW, SH = 503 * SC, 376 * SC
OX, OY = 2 + (60 - SW) / 2, 2


def T(fx, fy):
    """A point of the reference photo, as a fraction of its width and
    height, in 32x units."""
    return (OX + fx * SW, OY + fy * SH)


def glass(img, pts, k, inside):
    """A straight glass: inside(x, y) colours the contents, the two sides get
    a thin light edge."""
    xs = [round(x * k) for x, _ in pts]
    left, right = min(xs), max(xs)

    def paint(x, y):
        if x <= left or x >= right - 1:
            return C_GLASS
        return inside(x, y)
    poly(img, pts, k, paint)


def spaced(img, cx, y, word, color, k):
    """Wide-spaced capitals centred on cx: the 3 x 5 font at 32x, the outline
    font at 64x."""
    if k == 1:
        gap = 1
        width = len(word) * 3 + (len(word) - 1) * gap
        x = round(cx - width / 2)
        for ch in word:
            tiny(img, x, y, ch, color)
            x += 3 + gap
        return
    gap, size = 4, 11
    widths = [text_box(ch, size)[2] - text_box(ch, size)[0] for ch in word]
    x = round(cx - (sum(widths) + gap * (len(word) - 1)) / 2)
    for ch, w in zip(word, widths):
        text(img, x, y, ch, color, size)
        x += w + gap


def coffee(k=1):
    img = canvas(2, 1, C_WALL, k)
    W, H = img.size
    horizon = T(0, 0.44)[1]
    for y in range(H):
        for x in range(W):
            if y < horizon * k:
                c = C_WALL2 if ((x // (3 * k)) * 7 + (y // (2 * k)) * 3) % 11 == 0 else C_WALL
            else:
                n = ((x // k) * 37 + (y // k) * 53 + ((x // k) * (y // k)) % 7) % 23
                c = C_TABLE_D if n < 3 else (C_TABLE_L if n > 20 else C_TABLE)
            put(img, x, y, c)

    # iced black coffee, behind
    top, bot = T(0, 0.21)[1], T(0, 0.74)[1]

    def black(x, y):
        t = (y / k - top) / (bot - top)
        if t < 0.1:
            return C_ICE_D if (x + y) % 3 else (150, 120, 100)
        if t > 0.93:
            return (150, 104, 76)                    # the thick glass base
        c = tuple(round(a + (b - a) * t) for a, b in zip(C_BLACK, C_BLACK_LOW))
        if (x / k - T(0.27, 0)[0]) < 2.2 and t > 0.3:
            c = C_BLACK_GLOW
        return c
    glass(img, [T(0.26, 0.21), T(0.50, 0.21), T(0.49, 0.74), T(0.27, 0.74)], k, black)

    # milk jug, lower left
    jx0, jy0 = T(0.12, 0.67)
    jx1, jy1 = T(0.27, 0.90)
    hx0, hy0 = T(0.05, 0.69)
    hx1, hy1 = T(0.13, 0.82)
    oval(img, hx0, hy0, hx1, hy1, k, C_CHINA)                       # handle
    oval(img, hx0 + 0.9, hy0 + 0.9, hx1 - 0.4, hy1 - 0.9, k, C_TABLE)
    oval(img, jx0, jy0 - 0.5, jx1, jy1, k, lambda x, y: C_CHINA_D if x > (jx1 - 1.6) * k else C_CHINA)
    band(img, jx0 + 0.5, jx1 - 0.5, jy0, jy0 + 0.6, k, C_CHINA_D)    # the rim
    poly(img, [(jx1 - 1.2, jy0), (jx1 + 0.8, jy0 - 0.8), (jx1, jy0 + 1)], k, C_CHINA)   # spout

    # iced latte, in front
    ltop, lbot = T(0, 0.38)[1], T(0, 0.88)[1]

    def latte(x, y):
        t = (y / k - ltop) / (lbot - ltop)
        u = x / k
        if t < 0.15:                                 # ice above the coffee
            return C_ICE if (x // max(1, k) + y // max(1, k)) % 4 else C_ICE_D
        wave = 0.08 * math.sin(u * 1.7) + 0.05 * math.sin(u * 3.9)
        if t < 0.22 + wave:
            return C_ESPRESSO
        if t < 0.33 + wave:
            return C_TAN if (x + y) % 3 else C_ESPRESSO
        if t < 0.40 + wave:
            return C_CREAM
        if t > 0.95:
            return C_GLASS
        return C_MILK_D if u > T(0.66, 0)[0] else C_MILK
    glass(img, [T(0.45, 0.38), T(0.70, 0.38), T(0.69, 0.88), T(0.46, 0.88)], k, latte)

    # the pour: a small glass jug of espresso held by a hand from the top right
    sx, sy = T(0.60, 0.30)
    ex, ey = T(0.605, 0.44)
    for i in range(round(sy * k), round(ey * k) + 1):
        for j in range(max(1, k // 2 + (k > 1))):
            put(img, round(sx * k) + j, i, (88, 40, 18))
    poly(img, [T(0.56, 0.12), T(0.70, 0.07), T(0.74, 0.22), T(0.62, 0.31), T(0.58, 0.29)], k,
         lambda x, y: C_AMBER_L if x < T(0.62, 0)[0] * k and y < T(0, 0.2)[1] * k else C_AMBER)
    # the forearm leaves the picture through the top edge, up to the right
    poly(img, [T(0.63, 0.0), (52, 2), (49.6, 5.6), T(0.80, 0.22), T(0.74, 0.31), T(0.69, 0.33),
               T(0.67, 0.25), T(0.72, 0.18), T(0.66, 0.10)], k,
         lambda x, y: C_SKIN_D if x > 46 * k or (y > T(0, 0.24)[1] * k and x > T(0.72, 0)[0] * k) else C_SKIN)
    for fx, fy in ((0.69, 0.30), (0.72, 0.26)):                     # finger creases
        put(img, round(T(fx, fy)[0] * k), round(T(fx, fy)[1] * k), C_SKIN_D)

    # coffee beans
    for fx, fy in ((0.37, 0.80), (0.39, 0.865), (0.425, 0.855), (0.35, 0.915)):
        bx, by = T(fx, fy)
        if k == 1:
            put(img, math.floor(bx), math.floor(by), C_BEAN)
            put(img, math.floor(bx) + 1, math.floor(by), C_BEAN_D)
        else:
            oval(img, bx - 0.9, by - 0.6, bx + 0.9, by + 0.7, k, C_BEAN)
            put(img, round(bx * k) - 1, round(by * k), C_BEAN_D)
            put(img, round(bx * k), round(by * k), C_BEAN_D)

    # the name: a bean mark and COFFEE, white, wide-spaced
    cx = T(0.51, 0)[0]
    word_w = (6 * 3 + 5 * 1) if k == 1 else 60 / k
    mark_x = cx - word_w / 2 - 4
    ty = 25 if k == 1 else 51
    if k == 1:
        sprite(img, round(mark_x), ty, [".#.", "###", "###", ".#."], C_TEXT)
        spaced(img, cx + 1.5, ty, "COFFEE", C_TEXT, k)
    else:
        oval(img, mark_x - 1.6, 25.4, mark_x + 1.6, 29.6, k, C_TEXT)
        for i in range(-3, 4):
            put(img, round(mark_x * k) + (1 if i < 0 else 0) - (1 if i > 1 else 0), 55 + i, C_TABLE)
        spaced(img, (cx + 1.5) * k, ty + 1, "COFFEE", C_TEXT, k)
    return finish(img, k)


ADS = {"A1": mcdonalds, "A3": din_tai_fung, "A4": coffee}
TITLES = {"A1": "麥當勞（照作者給的照片）", "A3": "鼎泰豐（照作者給的橫幅）", "A4": "咖啡，萬用（照作者給的照片）"}
