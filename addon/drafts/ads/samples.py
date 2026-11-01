"""Three sample advertisements, each drawn at 16x and 32x, to decide the
texture resolution with the author before drawing the whole set.

Imported by build.py. Contents are placeholders for the discussion: only
world brands that already exist (Asuka Air, the northern snow country, the
cross-border limited express), no new names.
"""
from PIL import Image

from pixfont import frame, put, rect, text, text_width, tiny, tiny_width, vgrad, vtext

SILVER = (196, 200, 206)
WHITE = (250, 250, 248)
NAVY = (24, 44, 84)
TEAL = (0, 128, 140)
TEAL_DARK = (0, 96, 108)
GREY = (110, 116, 124)
SKY_TOP = (96, 160, 220)
SKY_DEEP = (34, 96, 176)
SKY_LOW = (200, 228, 246)
SNOW = (242, 246, 250)
SNOW_SHADE = (190, 204, 222)
ROCK = (120, 130, 150)
FOREST = (36, 78, 60)
SEA_TOP = (40, 120, 190)
SEA_LOW = (16, 60, 120)


def canvas(w, h, k):
    return Image.new("RGBA", (16 * w * k, 16 * h * k), WHITE + (255,))


# ---------- Asuka Air, 2 x 1 ----------

PLANE7 = ["...#...", "...#...", ".#####.", "#######", "...#...", "..###..", "...#..."]


def stamp(img, x, y, rows, color):
    for dy, row in enumerate(rows):
        for dx, c in enumerate(row):
            if c == "#":
                put(img, x + dx, y + dy, color)


def air_16():
    img = canvas(2, 1, 1)
    rect(img, 1, 1, 10, 15, TEAL)
    stamp(img, 2, 4, PLANE7, WHITE)
    tiny(img, 11, 3, "ASUKA", TEAL_DARK)
    tiny(img, 11, 9, "AIR", TEAL_DARK)
    frame(img, SILVER)
    return img


# Side view of an airliner, 20 x 7, white body with a teal tail.
JET = [
    "..TT................",
    "..TTT...............",
    "..TTTT..............",
    ".WWWWWWWWWWWWWWWWWW.",
    "WWWWWWWWWWWWWWWWWWWW",
    ".WWWWWWWWWWWWWWWWWW.",
    ".......GGGGGG.......",
]


def air_32():
    img = canvas(2, 1, 2)
    vgrad(img, 2, 2, 26, 18, SKY_TOP, SKY_LOW)
    vgrad(img, 2, 18, 26, 25, SEA_TOP, SEA_LOW)
    for dy, row in enumerate(JET):
        for dx, c in enumerate(row):
            col = {"T": TEAL, "W": WHITE, "G": (170, 178, 188)}.get(c)
            if col:
                put(img, 4 + dx, 6 + dy, col)
    for x in range(7, 22, 2):                   # windows
        put(img, x, 10, (90, 110, 140))
    text(img, 28, 4, "台北へ", NAVY, 11)
    text(img, 28, 16, "毎日運航", GREY, 8)
    rect(img, 2, 25, 62, 30, TEAL)              # brand bar
    tiny(img, 62 - 1 - tiny_width("ASUKA AIR"), 25, "ASUKA AIR", WHITE)
    frame(img, SILVER, 2)
    return img


# ---------- northern snow country, 1 x 2 ----------

def mountains(img, x0, x1, base, peaks, k):
    """Snowy ridges: peaks is a list of (x, height) in pixels."""
    for x in range(x0, x1):
        top = base
        for px, h in peaks:
            top = min(top, base - h + abs(x - px))
        for y in range(top, base):
            shade = (x - top) % 3 == 0 and y > top + k
            put(img, x, y, SNOW_SHADE if shade else SNOW)
        if top < base:
            put(img, x, top, SNOW)


def snow_16():
    img = canvas(1, 2, 1)
    vgrad(img, 1, 1, 15, 21, SKY_DEEP, SKY_LOW)
    mountains(img, 1, 15, 21, [(4, 6), (11, 4)], 1)
    rect(img, 1, 21, 15, 24, FOREST)
    for x in range(1, 15, 2):
        put(img, x, 20, FOREST)
    rect(img, 1, 24, 15, 31, SNOW)
    text(img, 2, 2, "雪", WHITE, 12)
    frame(img, SILVER)
    return img


def snow_32():
    img = canvas(1, 2, 2)
    vgrad(img, 2, 2, 30, 44, SKY_DEEP, SKY_LOW)
    mountains(img, 2, 30, 44, [(9, 16), (24, 8)], 2)
    for x in range(2, 30):
        for y in range(41 + (x * 7) % 3, 49):
            put(img, x, y, FOREST)
    for x in range(3, 30, 4):                   # tree tips
        put(img, x, 40, FOREST)
        put(img, x, 39 + (x % 2), FOREST)
    rect(img, 2, 49, 30, 62, SNOW)
    for x in range(4, 28, 5):
        put(img, x, 52 + x % 4, SNOW_SHADE)
    vtext(img, 23, 4, "北部の", WHITE, 10)      # read right column first
    vtext(img, 11, 4, "雪へ", WHITE, 10)
    frame(img, SILVER, 2)
    return img


# ---------- cross-border limited express, 4 x 2 ----------

def train(img, x0, x1, top, k):
    """Side view of a white EMU with a navy window band and a teal line;
    the nose slopes down to the right."""
    h = 10 * k
    for x in range(x0, x1):
        nose = x - (x1 - 8 * k)
        t = top + max(0, nose) // 1 if nose > 0 else top
        for y in range(t, top + h):
            put(img, x, y, WHITE)
        for y in range(max(t, top + 2 * k), top + 5 * k):
            put(img, x, y, NAVY)
        for y in range(top + 7 * k, top + 8 * k):
            put(img, x, y, TEAL)
    for y in range(top + h, top + h + k):
        rect(img, x0, y, x1 - 4 * k, y + 1, (60, 64, 70))
    for car in range(x0 + 20 * k, x1 - 10 * k, 20 * k):     # car joints
        rect(img, car, top, car + 1, top + h, (180, 186, 194))


def express_16():
    img = canvas(4, 2, 1)
    vgrad(img, 1, 1, 63, 31, SEA_TOP, SEA_LOW)
    train(img, 1, 63, 18, 1)
    text(img, 4, 3, "那覇へ直通", WHITE, 11)
    frame(img, SILVER)
    return img


def express_32():
    img = canvas(4, 2, 2)
    vgrad(img, 2, 2, 126, 62, SEA_TOP, SEA_LOW)
    train(img, 2, 126, 36, 2)
    for x in range(10, 110, 6):
        rect(img, x, 41, x + 4, 45, (120, 170, 220))   # windows catch the light
    text(img, 7, 6, "那覇・鹿児島へ", WHITE, 12)
    text(img, 7, 22, "海底トンネルで直通", (210, 230, 246), 10)
    frame(img, SILVER, 2)
    return img


SAMPLES = [
    # (label, w, h, {res: draw})
    ("Asuka Air（2 × 1）", 2, 1, {16: air_16, 32: air_32}),
    ("北部的雪（1 × 2）", 1, 2, {16: snow_16, 32: snow_32}),
    ("國際特急（4 × 2）", 4, 2, {16: express_16, 32: express_32}),
]
