"""Face parts for random NPC faces (proposal, see docs/npc.md).

Run from the repository root:
    python3 addon/drafts/npc/faces.py

Draws the parts a layered NPC skin would be built from and three preview
sheets:
    faces_hair.png   every hairstyle, front and back
    faces_parts.png  hair colours, skin tones, eyes, brows, make-up, age,
                     glasses, masks and other accessories
    faces_crowd.png  random NPCs in three outfits

Layers, bottom to top. In the game each would be a texture drawn by its own
render controller, the way the vanilla villager stacks its base, profession
and level textures:
    skin     the skin tone over the whole body
    face     eyes, brows, mouth, make-up, wrinkles, glasses, mask, earrings
    outfit   the slot's clothes and hat; transparent where skin shows
    hair     its own 64 x 64 texture: the head box (hair lying flat), a shell
             0.5 pixel larger (hair with volume) and extra boxes for long hair
             down the back, a ponytail and two kinds of bun
In this preview skin, face, outfit and the flat hair are composited into one
NPC texture, and the shell and the extra boxes are a second model,
hair_preview.geo.json. Under a cap or a helmet the hair is cut away where the
hat sits. The persona weights below are what the Molang choice in the game
would use; here Python's random stands in for the NPC's block position.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import build as b  # noqa: E402

TEX = ROOT / ".scratch" / "faces"
TEX_REL = "/.scratch/faces"

# ---------- palette (East Asian faces only, decided 2026-11-09) ----------

SKIN_TONES = {
    "fair": ("白皙", (246, 216, 190), 25),
    "light": ("偏白", (240, 204, 170), 35),
    "medium": ("一般", (232, 190, 152), 30),
    "tan": ("小麥色", (216, 172, 132), 10),
}
HAIR_COLOURS = {
    "black": ("黑", (36, 31, 32)),
    "dark_brown": ("深棕", (60, 42, 34)),
    "brown": ("棕", (100, 70, 50)),
    "milk_tea": ("奶茶色", (160, 128, 100)),
    "wine": ("酒紅", (92, 44, 44)),
    "grey": ("灰", (136, 134, 132)),
    "white": ("白", (212, 210, 206)),
}
EYE = (48, 36, 32)
EYE_WHITE = (238, 238, 236)
LASH = (34, 26, 28)
IRIS = (112, 74, 52)


def mix(a, c, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, c))


# ---------- hair: coverage on the head, flat or with volume ----------

HEAD_FACES = {"top": (8, 8), "front": (8, 10), "back": (8, 10), "right": (8, 10), "left": (8, 10)}
FLAT, VOL = 1, 2


class Hair:
    """Which head pixels have hair: FLAT on the head itself, VOL on the shell.
    On the top face row 0 is the back and row 7 the front."""

    def __init__(self, parts=(), shaved=False, tips=False, wave=None):
        self.g = {f: [[0] * w for _ in range(h)] for f, (w, h) in HEAD_FACES.items()}
        self.parts = set(parts)
        self.shaved = shaved      # flat hair shows the scalp (buzz cut, shaved sides)
        self.tips = tips          # pointed strand ends at the bottom of the sides and back
        self.wave = wave          # None, "wavy" (loose waves) or "curly" (a perm)

    def put(self, f, x, y, w, h, v):
        fw, fh = HEAD_FACES[f]
        for j in range(y, min(y + h, fh)):
            for i in range(x, min(x + w, fw)):
                self.g[f][j][i] = v
        return self

    def front(self, x, y, w=1, h=1, v=VOL):
        return self.put("front", x, y, w, h, v)

    def back(self, y, h, v=VOL):
        return self.put("back", 0, y, 8, h, v)

    def sides(self, fx, y, w, h, v=VOL):
        """Both sides, fx counted from the front edge of the side."""
        self.put("left", fx, y, w, h, v)
        return self.put("right", 8 - fx - w, y, w, h, v)

    def ring(self, y, h, v=VOL):
        for f in ("front", "back", "right", "left"):
            self.put(f, 0, y, 8, h, v)
        return self

    def top(self, v=VOL):
        return self.put("top", 0, 0, 8, 8, v)


def m_short():
    h = Hair().top().ring(0, 2)
    for x in (0, 1, 3, 6, 7):
        h.front(x, 2)
    h.sides(0, 2, 8, 1).sides(2, 3, 6, 1).sides(5, 4, 3, 3, FLAT).sides(2, 4, 1, 1, FLAT)
    return h.back(2, 4).back(6, 2, FLAT)


def m_center():
    h = Hair().top().ring(0, 2)
    h.front(0, 2, 3).front(5, 2, 3).front(0, 3, 2).front(6, 3, 2).front(0, 4).front(7, 4)
    h.sides(0, 2, 8, 3).sides(5, 5, 3, 1)
    return h.back(2, 5).back(7, 1, FLAT)


def m_comma():
    h = Hair().top().ring(0, 2)
    h.front(0, 2, 6).front(0, 3, 3).front(0, 4).front(7, 2)
    h.sides(0, 2, 8, 2).sides(5, 4, 3, 2)
    return h.back(2, 5).back(7, 1, FLAT)


def m_two_block():
    h = Hair(shaved=True).top().ring(0, 2)
    h.front(0, 2, 8).front(1, 3, 2).front(5, 3, 2)
    return h.sides(0, 2, 8, 5, FLAT).back(2, 6, FLAT)


def m_side_part():
    h = Hair().top().ring(0, 1)
    h.front(0, 1, 2).front(3, 1, 5).front(2, 1, 1, 1, FLAT)
    h.sides(0, 1, 8, 2).sides(5, 3, 3, 3, FLAT)
    return h.back(1, 4).back(5, 2, FLAT)


def m_buzz():
    h = Hair(shaved=True).top(FLAT).ring(0, 1, FLAT)
    return h.sides(1, 1, 7, 2, FLAT).sides(5, 3, 3, 3, FLAT).back(1, 6, FLAT)


def m_mash():
    h = Hair().top().ring(0, 3)
    h.front(0, 3, 8).front(0, 4).front(7, 4)
    return h.sides(0, 3, 8, 3).sides(2, 6, 6, 1).back(3, 5)


def m_balding():
    h = Hair()
    h.put("top", 0, 0, 8, 3, FLAT).put("top", 0, 0, 1, 8, FLAT).put("top", 7, 0, 1, 8, FLAT)
    h.sides(2, 1, 6, 1, FLAT).sides(5, 2, 3, 4)
    return h.back(1, 1, FLAT).back(2, 5)


def airy_bangs(h):
    """See-through bangs: a few thin strands below the hairline."""
    for x in (1, 4, 6):
        h.front(x, 3)
    return h


def strands(h, rows=5):
    """Thin strands just in front of the ears, framing the face."""
    return h.sides(0, 2, 1, rows)


def f_bob():
    h = Hair().top().ring(0, 3)
    for x in (0, 2, 3, 5, 7):
        h.front(x, 3)
    h.front(0, 4, 1, 5).front(7, 4, 1, 5)
    return h.sides(0, 3, 8, 6).back(3, 6)


def f_hime():
    h = Hair(parts=("back_long",)).top().ring(0, 4)                  # blunt bangs down to the brows
    h.front(0, 4, 1, 4).front(7, 4, 1, 4)                            # blunt side locks at the cheeks
    return h.sides(0, 4, 8, 6).back(4, 6)


def f_long_airy():
    h = airy_bangs(Hair(parts=("back_long", "locks_long"), tips=True).top().ring(0, 3))
    h.front(0, 3, 1, 7).front(7, 3, 1, 7)
    return h.sides(0, 3, 8, 7).back(3, 7)


def f_long_part():
    h = Hair(parts=("back_long", "locks_long"), tips=True).top().ring(0, 2)
    h.front(3, 0, 2, 2, FLAT)                                        # the parting
    h.front(0, 2, 3).front(5, 2, 3).front(0, 3, 2).front(6, 3, 2).front(0, 4, 1, 6).front(7, 4, 1, 6)
    return h.sides(0, 2, 8, 8).back(2, 8)


def f_wavy():
    h = Hair(parts=("back_mid",), tips=True, wave="wavy").top().ring(0, 3)
    h.front(0, 3, 4).front(7, 3).front(0, 4, 1, 5).front(7, 4, 1, 5)
    return h.sides(0, 3, 8, 7).back(3, 7)


def f_pony_high():
    h = strands(Hair(parts=("ponytail_high",)).top().ring(0, 2))
    h.front(0, 2, 3).front(0, 3).front(7, 2)
    h.sides(4, 2, 4, 3)
    return h.back(2, 4).back(6, 1, FLAT)


def f_pony_low():
    h = strands(Hair(parts=("ponytail",)).top().ring(0, 2))
    h.front(0, 2, 4).front(0, 3).front(7, 2, 1, 2)
    h.sides(4, 2, 4, 4)
    return h.back(2, 5)


def f_twin():
    h = airy_bangs(Hair(parts=("twins",)).top().ring(0, 3))
    h.sides(0, 3, 8, 2)
    h.back(3, 5).put("back", 3, 2, 2, 6, FLAT)                      # parted down the back
    return h


def f_bun_high():
    h = strands(Hair(parts=("bun_high",)).top().ring(0, 2))
    h.front(1, 2, 6).front(1, 3).front(6, 3)
    h.sides(4, 2, 4, 3)
    return h.back(2, 4).back(6, 1, FLAT)


def f_half_up():
    h = airy_bangs(Hair(parts=("back_long", "knot"), tips=True).top().ring(0, 3))
    h.front(0, 3, 1, 6).front(7, 3, 1, 6)
    return h.sides(0, 3, 8, 7).back(3, 7)


def f_bun_low():
    h = strands(Hair(parts=("bun_low",)).top().ring(0, 2), rows=3)
    h.front(0, 2, 4).front(7, 2)
    h.sides(4, 2, 4, 4)
    return h.back(2, 5)


def f_short():
    h = Hair(tips=True).top().ring(0, 3)
    h.front(0, 3, 3).front(7, 3).front(0, 4, 1, 3).front(7, 4, 1, 3)
    return h.sides(0, 3, 8, 4).back(3, 5)


def f_perm():
    h = Hair(wave="curly").top().ring(0, 3)
    h.front(0, 3).front(7, 3)
    return h.sides(0, 3, 8, 4).sides(4, 7, 4, 1).back(3, 5)


HAIRSTYLES = {
    "m_short": ("清爽短髮", m_short), "m_center": ("韓系中分", m_center), "m_comma": ("逗號瀏海", m_comma),
    "m_two_block": ("兩側推短", m_two_block), "m_side_part": ("旁分油頭", m_side_part), "m_buzz": ("平頭", m_buzz),
    "m_mash": ("蘑菇頭", m_mash), "m_balding": ("地中海", m_balding),
    "f_bob": ("內彎鮑伯頭", f_bob), "f_hime": ("姬髮型", f_hime), "f_long_airy": ("空氣瀏海長髮", f_long_airy),
    "f_long_part": ("韓系中分長髮", f_long_part), "f_wavy": ("中長捲髮", f_wavy), "f_pony_high": ("高馬尾", f_pony_high),
    "f_pony_low": ("低馬尾", f_pony_low), "f_twin": ("低雙馬尾", f_twin), "f_bun_high": ("丸子頭", f_bun_high),
    "f_half_up": ("公主頭", f_half_up), "f_bun_low": ("低盤髮", f_bun_low), "f_short": ("耳下短髮", f_short),
    "f_perm": ("燙髮", f_perm),
}

# The hair texture: the head box (same UV as the NPC head), the shell, and
# the extra boxes (u, v, width, height, depth).
HAIR_BOXES = {
    "head": (0, 0, 8, 10, 8), "shell": (32, 0, 8, 10, 8),
    "back_long": (0, 20, 9, 11, 1), "back_mid": (0, 34, 9, 5, 1),
    "ponytail": (20, 20, 2, 7, 2), "ponytail_high": (20, 30, 2, 10, 2),
    "bun_low": (30, 20, 4, 4, 3), "bun_high": (46, 20, 4, 3, 4),
    "locks_long": (30, 30, 1, 8, 1), "twins": (42, 30, 2, 5, 2), "knot": (52, 30, 3, 2, 1),
}
TIES = ("ponytail", "ponytail_high", "twins")
JAGGED = ("back_long", "back_mid", "locks_long")


class Tex(b.Skin):
    """A painter like build.Skin, for any box layout."""

    def __init__(self, seed, boxes):
        super().__init__(seed)
        self.boxes = boxes

    def rect(self, box, face):
        u, v, w, h, d = self.boxes[box]
        return {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h),
                "front": (u + d, v + d, w, h), "left": (u + d + w, v + d, d, h),
                "back": (u + 2 * d + w, v + d, w, h)}[face]

    def face_size(self, box, face):
        return self.rect(box, face)[2:]

    def paint(self, box, face, x, y, color, w=1, h=1, grain=0):
        fx, fy, _, _ = self.rect(box, face)
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.dot(fx + i, fy + j, color, grain)


def hair_layer(look, hat=None, seed=0):
    """The hair texture for one look; returns (Tex, extra bones to show).
    Shading: an angel ring of highlights across row 2, darker ends, thin
    strands down the sides and back, and pointed tips where the style has them."""
    h = HAIRSTYLES[look["hair"]][1]()
    if hat:
        rows = 4 if hat == "helmet" else 3
        h.put("top", 0, 0, 8, 8, 0).ring(0, rows, 0)
        if hat == "cap":
            h.front(0, 3, 8, 1, 0)                # visor
        h.parts -= {"bun_high", "knot"}
    base = HAIR_COLOURS[look["hair_colour"]][1]
    skin = SKIN_TONES[look["skin"]][1]
    dark, mid_dark = b.shade(base, -2), b.shade(base, -1)
    light, shine = b.shade(base, 2), b.shade(base, 4)
    flat = mix(base, skin, 0.45) if h.shaved else mid_dark
    t = Tex(seed, HAIR_BOXES)
    for f, (fw, fh) in HEAD_FACES.items():
        for y in range(fh):
            for x in range(fw):
                v = h.g[f][y][x]
                if v >= FLAT:
                    t.paint("head", f, x, y, flat, grain=3)
                if v != VOL:
                    continue
                if f == "top":
                    c = light if (y >= 5 and x % 3 == 1) else base
                else:
                    end = y + 1 == fh or h.g[f][y + 1][x] != VOL
                    if end and h.tips and f != "front" and y >= 4 and x % 2:
                        continue                  # a strand tip: the flat hair shows behind it
                    if end:
                        c = mid_dark if f == "front" else dark
                    elif y == 2:
                        c = shine if x % 2 == 0 else light
                    elif y == 1:
                        c = light if x % 3 == 0 else base
                    elif h.wave == "wavy" and y >= 4:
                        c = (light, base, mid_dark, base)[(x + y) % 4]
                    elif h.wave == "curly":
                        c = {0: light, 1: mid_dark}.get((x * 7 + y * 13) % 5, base)
                    elif y >= 3 and f != "front" and (x + y // 3) % 3 == 0:
                        c = mid_dark
                    else:
                        c = base
                t.paint("shell", f, x, y, c, grain=3)
    for part in h.parts:
        t.fill(part, base, grain=3)
        _, ph = t.face_size(part, "front")
        for f in b.SIDES:
            fw, _ = t.face_size(part, f)
            for x in range(fw):
                if x % 2:
                    t.paint(part, f, x, 1, mid_dark, 1, ph - 2, grain=2)          # strands
                if part in JAGGED and x % 2:
                    t.paint(part, f, x, ph - 1, None)                                # pointed ends
                else:
                    t.paint(part, f, x, ph - 1, dark, grain=2)
        if part in TIES:
            t.ring(part, 0, look.get("tie") or (40, 40, 44), 1, grain=1)
        if part.startswith("bun"):                                                  # a twist
            t.paint(part, "back", 1, 1, dark, 2, 1)
            t.paint(part, "back", 1, 2, dark)
    if look.get("pin") and h.g["front"][2][5] == VOL:                               # hair pin
        t.paint("shell", "front", 5, 2, look["pin"], 2, 1)
    return t, ["shell"] + sorted(h.parts)


# ---------- face ----------

def side(s, fx, y, color, w=1, h=1, grain=0):
    """Paint both sides of the head, fx counted from the front edge."""
    s.paint("head", "left", fx, y, color, w, h, grain)
    s.paint("head", "right", 8 - fx - w, y, color, w, h, grain)


def paint_face(s, look):
    """Skin tone on the whole head and the face details. Rows: 3 brows,
    4 eyes, 6 cheeks, 8 mouth, 9 chin; the ear is at 3-4 from the front."""
    skin = SKIN_TONES[look["skin"]][1]
    hair = HAIR_COLOURS[look["hair_colour"]][1]
    s.fill("head", skin, grain=1)
    s.paint("head", "bottom", 0, 0, b.shade(skin, -2), 8, 8, grain=1)
    side(s, 3, 4, b.shade(skin, -2), 2, 2)                    # ears
    side(s, 3, 5, b.shade(skin, -4))
    brow = b.shade(hair, -1) if look["brows"] == "thick" else mix(skin, hair, 0.55)
    if look["eyes"] == "lash":
        brow = mix(skin, hair, 0.4)               # soft brows above the lash line
    if look["hair_colour"] in ("grey", "white"):
        brow = mix(skin, hair, 0.7)
    s.both("head", 1, 3, brow, 2, 1)
    if look["eyes"] == "lash":                    # lash line over a white and a brown iris
        s.both("head", 0, 4, LASH, 3, 1)          # flicks out at the outer corner
        s.both("head", 1, 5, EYE_WHITE)
        s.both("head", 2, 5, IRIS)
    elif look["eyes"] == "narrow":
        s.both("head", 1, 4, mix(EYE, skin, 0.25), 2, 1)
    else:
        s.both("head", 1, 4, EYE_WHITE)
        s.both("head", 2, 4, EYE)
        if look["eyes"] == "round":
            s.both("head", 1, 5, mix(EYE_WHITE, skin, 0.4))
            s.both("head", 2, 5, EYE)
    mouth = b.shade(skin, -4)
    if look.get("gender") == "f":
        mouth = mix(skin, (200, 110, 110), 0.35)
    if look["mouth"] == "lips":
        mouth = mix(skin, (196, 92, 96), 0.7)
    s.paint("head", "front", 3, 8, mouth, 2, 1)
    if look["mouth"] == "smile":
        s.both("head", 2, 7, b.shade(skin, -3))
    if look.get("blush"):
        s.both("head", 1, 6, mix(skin, (240, 140, 140), 0.45))
        s.both("head", 0, 6, mix(skin, (240, 140, 140), 0.25))
    if look.get("wrinkles"):
        s.both("head", 2, 7, b.shade(skin, -3))
        if look["wrinkles"] == "old":
            s.both("head", 0, 4, b.shade(skin, -3))
            s.paint("head", "front", 2, 2, b.shade(skin, -2), 4, 1)
    if look.get("mole"):
        x, y = look["mole"]
        s.paint("head", "front", x, y, b.shade(skin, -9))
    if look.get("stubble"):
        st = mix(skin, hair, 0.35)
        s.paint("head", "front", 1, 8, st, 2, 2)
        s.paint("head", "front", 5, 8, st, 2, 2)
        s.paint("head", "front", 3, 9, st, 2, 1)
        side(s, 0, 7, st, 3, 3)
    glasses = look.get("glasses")
    if glasses:
        frame = {"black": (40, 38, 44), "metal": (168, 160, 140), "sun": (40, 40, 46)}[glasses]
        s.both("head", 0, 4, frame)
        s.paint("head", "front", 3, 4, frame, 2, 1)
        if glasses == "black":                    # round rims above and below, corners open
            s.both("head", 1, 3, frame, 2, 1)
            s.both("head", 1, 5, frame, 2, 1)
        elif glasses == "metal":
            s.both("head", 1, 5, frame, 2, 1)
        else:
            s.both("head", 1, 4, (54, 62, 76), 2, 2)
        side(s, 0, 4, frame, 3, 1)
    mask = look.get("mask")
    if mask:
        c = {"white": (236, 238, 240), "black": (44, 44, 48)}[mask]
        s.paint("head", "front", 0, 6, c, 8, 4, grain=1)
        s.paint("head", "front", 1, 7, b.shade(c, -2), 6, 1)
        s.paint("head", "front", 1, 9, b.shade(c, -2), 6, 1)
        side(s, 0, 6, c, 4, 1)
    if look.get("earrings"):
        side(s, 3, 6, {"gold": (222, 184, 84), "silver": (206, 210, 216)}[look["earrings"]])


# ---------- a random look ----------

def pick(rng, table):
    keys = list(table)
    return rng.choices(keys, weights=[table[k] for k in keys])[0]


HAIR_POOLS = {
    ("m", "young"): {"m_short": 25, "m_center": 20, "m_comma": 20, "m_two_block": 20, "m_mash": 15},
    ("m", "middle"): {"m_short": 35, "m_side_part": 30, "m_two_block": 15, "m_buzz": 10, "m_center": 10},
    ("m", "old"): {"m_short": 30, "m_side_part": 25, "m_buzz": 20, "m_balding": 25},
    ("f", "young"): {"f_long_airy": 14, "f_long_part": 12, "f_hime": 6, "f_bob": 10, "f_wavy": 10,
                     "f_pony_high": 10, "f_pony_low": 6, "f_twin": 6, "f_bun_high": 10, "f_half_up": 10,
                     "f_short": 6},
    ("f", "middle"): {"f_bob": 20, "f_wavy": 15, "f_pony_low": 15, "f_bun_low": 20, "f_short": 15,
                      "f_long_part": 10, "f_perm": 5},
    ("f", "old"): {"f_short": 30, "f_perm": 35, "f_bun_low": 20, "f_bob": 15},
}
COLOUR_POOLS = {
    "young": {"black": 30, "dark_brown": 25, "brown": 20, "milk_tea": 15, "wine": 10},
    "middle": {"black": 45, "dark_brown": 30, "brown": 15, "grey": 10},
    "old": {"grey": 45, "white": 30, "black": 15, "dark_brown": 10},
}
EYE_POOLS = {
    ("m", "other"): {"normal": 60, "narrow": 25, "round": 15}, ("m", "old"): {"normal": 60, "narrow": 40},
    ("f", "other"): {"lash": 60, "normal": 20, "narrow": 20}, ("f", "old"): {"normal": 50, "narrow": 30, "lash": 20},
}
PIN_COLOURS = [(226, 120, 140), (240, 210, 120), (36, 36, 40), (140, 180, 220)]


def random_look(rng, gender=None, age=None, hair=None, casual=False):
    """A random persona: gender style and age first, then features drawn from
    pools that depend on them. Sunglasses only in casual slots."""
    gender = gender or rng.choice("mf")
    age = age or pick(rng, {"young": 35, "middle": 35, "old": 30})
    female = gender == "f"
    look = {
        "gender": gender, "age": age,
        "skin": pick(rng, {k: v[2] for k, v in SKIN_TONES.items()}),
        "hair": hair or pick(rng, HAIR_POOLS[(gender, age)]),
        "hair_colour": pick(rng, COLOUR_POOLS[age]),
        "eyes": pick(rng, EYE_POOLS[(gender, "old" if age == "old" else "other")]),
        "brows": pick(rng, {"thin": 70, "thick": 30} if female else {"thick": 65, "thin": 35}),
        "mouth": pick(rng, {"lips": 45, "smile": 20, "normal": 35} if female and age != "old"
                      else {"normal": 70, "smile": 30}),
    }
    if female and age != "old" and rng.random() < (0.5 if age == "young" else 0.2):
        look["blush"] = True
    if age == "old" or (age == "middle" and rng.random() < 0.3):
        look["wrinkles"] = "old" if age == "old" else "middle"
    if rng.random() < {"young": 0.25, "middle": 0.35, "old": 0.45}[age]:
        look["glasses"] = pick(rng, {"black": 45, "metal": 45, "sun": 10 if casual else 0})
    if rng.random() < 0.12:
        look["mask"] = pick(rng, {"white": 75, "black": 25})
    if female and rng.random() < 0.35:
        look["earrings"] = rng.choice(["gold", "silver"])
    if female and age == "young" and rng.random() < 0.25:
        look["pin"] = rng.choice(PIN_COLOURS)
    if not female and age != "young" and rng.random() < 0.12:
        look["stubble"] = True
    if rng.random() < 0.08:
        look["mole"] = rng.choice([(6, 6), (1, 7), (5, 5), (2, 6)])
    return look


# ---------- outfits for the previews (the slot's layer) ----------

def outfit_plain(s, look, rng):
    tee = (150, 156, 164)
    b.shirt(s, tee)
    skin = SKIN_TONES[look["skin"]][1]
    b.sleeves(s, tee, short=True, hands=skin, skin=skin)
    b.trousers(s, (60, 62, 70))
    return None


def outfit_staff(s, look, rng):
    b.cap(s, b.NAVY, (92, 150, 210), badge=b.GOLD)
    b.shirt(s, b.WHITE_SHIRT)
    b.tie(s, (54, 92, 150))
    b.blazer(s, b.NAVY, rows=14, v=4, lining=b.shade(b.NAVY, 2), buttons=b.GOLD)
    b.sleeves(s, b.NAVY, cuff=b.WHITE_SHIRT, hands=(244, 244, 244))
    b.trousers(s, b.NAVY)
    return "cap"


def outfit_office(s, look, rng):
    skin = SKIN_TONES[look["skin"]][1]
    suit = rng.choice([(46, 54, 76), (58, 60, 66), (36, 38, 44), (120, 112, 100)])
    b.shirt(s, b.WHITE_SHIRT)
    if look["gender"] == "m":
        b.tie(s, rng.choice([(150, 50, 56), (54, 92, 150), (70, 70, 76)]))
        b.blazer(s, suit, rows=14, v=4)
        b.sleeves(s, suit, cuff=b.WHITE_SHIRT, hands=skin, skin=skin)
        b.trousers(s, suit)
    else:
        b.blazer(s, suit, rows=16, v=3)
        s.ring("robe", 12, b.shade(suit, -1), 4, grain=3)
        s.paint("robe", "front", 3, 12, b.shade(suit, -1), 2, 4, grain=3)
        b.sleeves(s, suit, cuff=b.WHITE_SHIRT, hands=skin, skin=skin)
        b.trousers(s, mix(skin, (60, 50, 50), 0.25), shoe=(30, 28, 30), shoe_rows=1, grain=1)
    return None


def outfit_citizen(s, look, rng):
    skin = SKIN_TONES[look["skin"]][1]
    top = rng.choice([(240, 180, 70), (110, 150, 200), (226, 222, 212), (200, 96, 90), (120, 160, 110),
                      (60, 64, 72), (236, 200, 210)])
    b.shirt(s, top)
    if rng.random() < 0.5:
        b.sleeves(s, top, short=True, hands=skin, skin=skin)
    else:
        b.sleeves(s, top, hands=skin)
    if look["gender"] == "f" and rng.random() < 0.4:
        sk = rng.choice([(60, 64, 80), (200, 180, 150), (140, 90, 100)])
        s.ring("robe", 12, sk, 4, grain=3)
        b.trousers(s, skin, shoe=rng.choice([(236, 236, 232), (40, 38, 40)]), grain=1)
    else:
        b.trousers(s, rng.choice([(70, 100, 150), (60, 60, 66), (190, 170, 130)]),
                   shoe=rng.choice([(236, 236, 232), (40, 38, 40)]))
    return None


# ---------- preview ----------

def box_faces(u, v, w, h, d):
    def f(x, y, a, c):
        return {"uv": [x, y], "uv_size": [a, c]}
    return {"up": f(u + d + w, v + d, -w, -d), "down": f(u + d + w, v, w, d),
            "east": f(u, v + d, d, h), "north": f(u + d, v + d, w, h),
            "west": f(u + d + w, v + d, d, h), "south": f(u + 2 * d + w, v + d, w, h)}


def hair_cube(box, origin, size, inflate=0.0):
    return {"origin": [a - inflate for a in origin], "size": [a + 2 * inflate for a in size],
            "uv": box_faces(*HAIR_BOXES[box])}


HAIR_GEO = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.npc_hair_preview", "texture_width": 64, "texture_height": 64},
    "bones": [
        {"name": "shell", "pivot": [0, 24, 0], "cubes": [hair_cube("shell", [-4, 24, -4], [8, 10, 8], 0.5)]},
        {"name": "back_long", "pivot": [0, 24, 0], "cubes": [hair_cube("back_long", [-4.5, 13, 3.6], [9, 11, 1])]},
        {"name": "back_mid", "pivot": [0, 24, 0], "cubes": [hair_cube("back_mid", [-4.5, 19, 3.6], [9, 5, 1])]},
        {"name": "locks_long", "pivot": [0, 24, 0], "cubes": [
            hair_cube("locks_long", [3.2, 16, -4.4], [1.2, 8, 1.2]),
            hair_cube("locks_long", [-4.4, 16, -4.4], [1.2, 8, 1.2])]},
        {"name": "ponytail", "pivot": [0, 24, 0], "cubes": [hair_cube("ponytail", [-1, 21, 4.5], [2, 7, 2])]},
        {"name": "ponytail_high", "pivot": [0, 24, 0], "cubes": [hair_cube("ponytail_high", [-1, 22, 4.6], [2, 10, 2])]},
        {"name": "twins", "pivot": [0, 24, 0], "cubes": [
            hair_cube("twins", [3.4, 19.5, -4.2], [2, 5, 2]), hair_cube("twins", [-5.4, 19.5, -4.2], [2, 5, 2])]},
        {"name": "bun_low", "pivot": [0, 24, 0], "cubes": [hair_cube("bun_low", [-2, 25, 4.5], [4, 4, 3])]},
        {"name": "bun_high", "pivot": [0, 24, 0], "cubes": [hair_cube("bun_high", [-2, 34.3, -1], [4, 3.5, 4])]},
        {"name": "knot", "pivot": [0, 24, 0], "cubes": [hair_cube("knot", [-1.5, 29, 4.5], [3, 2, 1.2])]},
    ]}]}


def make_npc(name, look, outfit, rng):
    """Write the NPC texture and the hair texture; return the two preview objects."""
    s = b.Skin(rng.randrange(10 ** 6))
    paint_face(s, look)
    hat = outfit(s, look, rng)
    hair, bones = hair_layer(look, hat, rng.randrange(10 ** 6))
    s.img.alpha_composite(hair.img.crop((0, 0, 32, 18)), (0, 0))     # flat hair on the head
    s.img.save(TEX / f"{name}.png")
    hair.img.save(TEX / f"{name}_hair.png")
    common = {"type": "geo", "rotationY": 180}
    return [dict(common, geo=f"{b.REL}/npc_preview.geo.json", texture=f"{TEX_REL}/{name}.png"),
            dict(common, geo=f"{b.REL}/hair_preview.geo.json", texture=f"{TEX_REL}/{name}_hair.png", bones=bones)]


HEAD_CAM = {"elevation": 8, "size": 27, "target": [0, 26, 0]}


def base_look(**kw):
    look = {"gender": "m", "age": "young", "skin": "light", "hair": "m_short", "hair_colour": "dark_brown",
            "eyes": "normal", "brows": "thick", "mouth": "normal"}
    look.update(kw)
    return look


def style_code(k):
    """M1 ... M8, F1 ... F13: what the author can point at."""
    same = [n for n in HAIRSTYLES if n[0] == k[0]]
    return f"{k[0].upper()}{same.index(k) + 1}"


def hair_sheet(gender, per_row):
    names = [k for k in HAIRSTYLES if k.startswith(gender + "_")]
    panels = []
    for i in range(0, len(names), per_row):
        group = names[i:i + per_row]
        for az, view in ((20, "正面"), (200, "背面")):
            for k in group:
                if gender == "f":
                    look = base_look(hair=k, gender="f", eyes="lash", brows="thin",
                                     age="old" if k == "f_perm" else "young")
                else:
                    look = base_look(hair=k, age="old" if k == "m_balding" else "young")
                objs = make_npc(f"hair_{k}", look, outfit_plain, random.Random(1))
                label = f"{style_code(k)} {HAIRSTYLES[k][0]}" if view == "正面" else f"{style_code(k)}（背面）"
                panels.append({"label": label, "camera": dict(HEAD_CAM, azimuth=az), "objects": objs})
            panels += [{"label": "", "objects": []}] * (per_row - len(group))
    title = "女生的髮型（日韓系，第二版）" if gender == "f" else "男生的髮型（日韓系）"
    return {"title": f"隨機臉的零件：{title}", "columns": per_row, "panelWidth": 165, "panelHeight": 180,
            "background": "#e8edf1", "panels": panels}


def parts_sheet(rng):
    items = []
    for k, (n, _) in HAIR_COLOURS.items():
        items.append((f"髮色：{n}", base_look(hair="m_center", hair_colour=k)))
    for k, (n, _, _) in SKIN_TONES.items():
        items.append((f"膚色：{n}", base_look(skin=k)))
    for k, n in (("normal", "一般"), ("narrow", "細長"), ("round", "大眼")):
        items.append((f"眼睛：{n}", base_look(eyes=k)))
    items.append(("眼睛：睫毛（女生）", base_look(eyes="lash", hair="f_bob", gender="f", brows="thin")))
    for k, n in (("thick", "粗"), ("thin", "細")):
        items.append((f"眉毛：{n}", base_look(brows=k, hair="f_bob", gender="f")))
    items += [
        ("嘴：微笑", base_look(mouth="smile")),
        ("口紅", base_look(mouth="lips", hair="f_long_part", gender="f", brows="thin", eyes="lash")),
        ("腮紅", base_look(blush=True, mouth="lips", hair="f_bob", gender="f", brows="thin", eyes="lash")),
        ("中年：法令紋", base_look(wrinkles="middle", hair="m_side_part", hair_colour="black")),
        ("年長：皺紋、白髮", base_look(wrinkles="old", hair="m_balding", hair_colour="white", age="old")),
        ("痣", base_look(mole=(6, 6))),
        ("鬍渣", base_look(stubble=True, hair="m_side_part", hair_colour="black")),
        ("眼鏡：黑框", base_look(glasses="black")),
        ("眼鏡：金屬細框", base_look(glasses="metal", hair="f_bob", gender="f", brows="thin", eyes="lash")),
        ("太陽眼鏡", base_look(glasses="sun", hair="m_two_block")),
        ("口罩：白", base_look(mask="white", hair="m_mash")),
        ("口罩：黑", base_look(mask="black", hair="m_center")),
        ("耳環", base_look(earrings="gold", hair="f_pony_high", gender="f", brows="thin", eyes="lash")),
        ("髮夾", base_look(pin=PIN_COLOURS[0], hair="f_long_airy", gender="f", brows="thin", eyes="lash")),
    ]
    panels = []
    for i, (label, look) in enumerate(items):
        objs = make_npc(f"part_{i}", look, outfit_plain, random.Random(2))
        panels.append({"label": label, "camera": dict(HEAD_CAM, azimuth=25), "objects": objs})
    panels += [{"label": "", "objects": []}] * (-len(panels) % 8)
    return {"title": "隨機臉的零件：髮色、膚色、五官、年齡、配件（示意）", "columns": 8, "panelWidth": 160,
            "panelHeight": 170, "background": "#e8edf1", "panels": panels}


def crowd_sheet(rng):
    panels = []
    for outfit, label in ((outfit_staff, "站務員"), (outfit_office, "上班族"), (outfit_citizen, "市民")):
        for i in range(8):
            look = random_look(rng, casual=outfit is outfit_citizen)
            objs = make_npc(f"crowd_{label}_{i}", look, outfit, rng)
            tags = [HAIRSTYLES[look["hair"]][0], HAIR_COLOURS[look["hair_colour"]][0]]
            panels.append({"label": "・".join(tags),
                           "camera": {"azimuth": 20, "elevation": 8, "size": 40, "target": [0, 17, 0]},
                           "objects": objs})
    return {"title": "隨機組合（示意）：上排站務員、中排上班族、下排市民，同一排是同一套衣服", "columns": 8,
            "panelWidth": 165, "panelHeight": 240, "background": "#e8edf1", "panels": panels}


def render(name, sheet):
    (HERE / f"{name}.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    subprocess.run(["node", str(ROOT / "tools/preview/render.mjs"), str(HERE / f"{name}.json"),
                    str(HERE / f"{name}.png")], check=True, cwd=ROOT)


def main():
    TEX.mkdir(parents=True, exist_ok=True)
    (HERE / "hair_preview.geo.json").write_text(json.dumps(HAIR_GEO, indent=1) + "\n", encoding="utf-8")
    rng = random.Random(1109)
    render("faces_hair_m", hair_sheet("m", 8))
    render("faces_hair_f", hair_sheet("f", 7))
    render("faces_parts", parts_sheet(rng))
    render("faces_crowd", crowd_sheet(rng))


if __name__ == "__main__":
    main()
