"""Build the NPC skin drafts and their preview sheets.

Run from the repository root:
    python3 addon/drafts/npc/build.py

Resource pack only: each skin replaces one of the 60 vanilla NPC skins
(textures/entity/npc/*.png). The NPC itself stays vanilla, so the vanilla
export simply shows the vanilla skins again.

The NPC is not a player model. It uses geometry.npc, a villager-shaped model:
    head   8 x 10 x 8, box UV (0, 0), plus a 2 x 4 x 2 nose at (24, 0) that
           sticks out of the lower face and hangs 1 pixel below the chin
    body   8 x 12 x 6 at (16, 20)
    robe   8 x 18 x 6 at (0, 38), inflated 0.5: an outer layer from the
           shoulders to 6 pixels above the ground (coats, jackets, skirts)
    arms   always folded: a 8 x 4 x 4 forearm bar at (40, 38) between two
           4 x 8 x 4 upper arms at (44, 22) and (44, 46), tilted 43 degrees
           forward by the vanilla animation
    legs   4 x 12 x 4 at (0, 22), both legs share the same texture
    jacket 8 x 12 x 4 at (16, 32), inflated 0.25, mostly hidden inside the
           body; its UV overlaps the body and robe areas
The hat layer (32, 0) and the pants layers exist in the file but are not
drawn (hat) or hidden by the render controller (pants), so they stay empty.

Skins are drawn in code from the pieces below and written to skins/<id>.png;
which vanilla slot each one replaces is recorded in docs/npc.md. Colours get
a faint per-pixel grain, like the other drafts. compare_no_nose.png is the
station staff with the nose left transparent, only for the comparison panel.

npc_preview.geo.json rebuilds geometry.npc for the preview tool only: the
inflation and the folded-arm pose are baked in, rotations use the preview
tool's sign, and the model faces -z.
"""
import json
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REL = "/addon/drafts/npc"
SKINS = HERE / "skins"

# Box UV of geometry.npc: u, v, width, height, depth.
BOXES = {
    "head": (0, 0, 8, 10, 8), "nose": (24, 0, 2, 4, 2), "body": (16, 20, 8, 12, 6),
    "robe": (0, 38, 8, 18, 6), "jacket": (16, 32, 8, 12, 4), "bar": (40, 38, 8, 4, 4),
    "arm_r": (44, 22, 4, 8, 4), "arm_l": (44, 46, 4, 8, 4), "leg": (0, 22, 4, 12, 4),
}
SIDES = ("right", "front", "left", "back")


def face_rect(box, face):
    """x, y, w, h of one face in the 64 x 64 texture. Seen from outside, the
    front's x = 0 is the character's right; on the right face x = 0 is the
    back edge, on the left face x = 0 is the front edge."""
    u, v, w, h, d = BOXES[box]
    return {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h),
            "front": (u + d, v + d, w, h), "left": (u + d + w, v + d, d, h),
            "back": (u + 2 * d + w, v + d, w, h)}[face]


def shade(c, k):
    """Darken (k < 0) or lighten (k > 0) a colour by k steps of 8."""
    return tuple(max(0, min(255, x + 8 * k)) for x in c)


class Skin:
    def __init__(self, seed):
        self.img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        self.rng = random.Random(seed)

    def dot(self, x, y, color, grain=0):
        if color is None:
            self.img.putpixel((x, y), (0, 0, 0, 0))
            return
        d = self.rng.randint(-grain, grain) if grain else 0
        self.img.putpixel((x, y), tuple(max(0, min(255, c + d)) for c in color[:3]) + (255,))

    def paint(self, box, face, x, y, color, w=1, h=1, grain=0):
        fx, fy, fw, fh = face_rect(box, face)
        for j in range(y, y + h):
            for i in range(x, x + w):
                if not (0 <= i < fw and 0 <= j < fh):
                    raise ValueError(f"{box}.{face} ({i}, {j}) is outside {fw} x {fh}")
                self.dot(fx + i, fy + j, color, grain)

    def face_size(self, box, face):
        return face_rect(box, face)[2:]

    def fill(self, box, color, faces=("top", "bottom") + SIDES, grain=3):
        for f in faces:
            w, h = self.face_size(box, f)
            self.paint(box, f, 0, 0, color, w, h, grain)

    def ring(self, box, y, color, h=1, grain=3):
        """Paint rows y .. y+h-1 all the way round the four sides."""
        for f in SIDES:
            w, _ = self.face_size(box, f)
            self.paint(box, f, 0, y, color, w, h, grain)

    def both(self, box, x, y, color, w=1, h=1, grain=0):
        """Paint a front detail and its mirror image."""
        fw, _ = self.face_size(box, "front")
        self.paint(box, "front", x, y, color, w, h, grain)
        self.paint(box, "front", fw - x - w, y, color, w, h, grain)

    def save(self, name):
        SKINS.mkdir(exist_ok=True)
        self.img.save(SKINS / f"{name}.png")


# ---------- palette ----------

SKIN = (234, 194, 158)
SKIN_TAN = (214, 168, 128)
HAIR_BLACK = (44, 36, 34)
HAIR_BROWN = (78, 54, 40)
HAIR_GREY = (150, 148, 146)
EYE_WHITE = (238, 238, 236)
EYE = (52, 40, 34)
WHITE_SHIRT = (236, 238, 240)
NAVY = (38, 50, 82)
BLACK_SUIT = (36, 38, 46)
SHOE = (34, 32, 34)
GOLD = (214, 172, 72)


# ---------- head ----------

def side_hair(s, hair, top_rows, back_rows, ear=True, skin=SKIN):
    """Hair on both sides of the head: full width for top_rows, then only the
    back half down to back_rows; an ear just in front of it."""
    for f in ("right", "left"):
        s.paint("head", f, 0, 0, hair, 8, top_rows, grain=4)
        back = 0 if f == "right" else 4      # x = 0 is the back edge on the right side
        s.paint("head", f, back, top_rows, hair, 4, back_rows - top_rows, grain=4)
        if ear:
            ex = 4 if f == "right" else 2
            s.paint("head", f, ex, top_rows + 1, shade(skin, -2), 2, 2)
            s.paint("head", f, ex + (1 if f == "right" else 0), top_rows + 1, shade(skin, -4), 1, 1)


def head(s, skin=SKIN, hair=HAIR_BLACK, style="short", eyes=EYE, nose=True, brows=True):
    """Face rows: 0-2 hair, 3 brows, 4 eyes, 7-9 behind the nose, 9 chin."""
    s.fill("head", skin, grain=1)
    hs = shade(hair, -1)
    s.paint("head", "top", 0, 0, hair, 8, 8, grain=4)
    if style == "short":
        s.paint("head", "front", 0, 0, hair, 8, 2, grain=4)
        s.paint("head", "front", 0, 2, hair, 2, 1, grain=4)
        s.paint("head", "front", 5, 2, hair, 1, 1, grain=4)
        s.paint("head", "front", 7, 2, hair, 1, 2, grain=4)
        side_hair(s, hair, 3, 7, skin=skin)
        s.paint("head", "back", 0, 0, hair, 8, 8, grain=4)
        s.paint("head", "back", 1, 8, hs, 6, 1, grain=4)
    elif style == "cropped":
        s.paint("head", "front", 0, 0, hair, 8, 1, grain=4)
        s.paint("head", "front", 0, 1, hair, 1, 2, grain=4)
        s.paint("head", "front", 7, 1, hair, 1, 2, grain=4)
        side_hair(s, hair, 2, 6, skin=skin)
        s.paint("head", "back", 0, 0, hair, 8, 7, grain=4)
    elif style == "bob":
        s.paint("head", "front", 0, 0, hair, 8, 3, grain=4)
        s.paint("head", "front", 2, 2, skin, 1, 1, grain=1)
        s.paint("head", "front", 5, 2, skin, 1, 1, grain=1)
        s.paint("head", "front", 0, 3, hair, 1, 6, grain=4)
        s.paint("head", "front", 7, 3, hair, 1, 6, grain=4)
        side_hair(s, hair, 9, 9, ear=False, skin=skin)
        s.paint("head", "back", 0, 0, hair, 8, 9, grain=4)
        s.paint("head", "back", 0, 8, hs, 8, 1, grain=4)
    elif style == "bun":
        # hair pulled back into a low bun, the bun painted on the back
        s.paint("head", "front", 0, 0, hair, 8, 2, grain=4)
        s.paint("head", "front", 0, 2, hair, 4, 1, grain=4)
        s.paint("head", "front", 7, 2, hair, 1, 2, grain=4)
        s.paint("head", "front", 0, 3, hair, 1, 1, grain=4)
        side_hair(s, hair, 3, 7, skin=skin)
        s.paint("head", "back", 0, 0, hair, 8, 8, grain=4)
        s.paint("head", "back", 2, 5, hs, 4, 3)
        s.paint("head", "back", 3, 5, shade(hair, 1), 2, 1)
        s.paint("head", "back", 2, 8, hs, 4, 1)
    if brows:
        s.both("head", 1, 3, hs, 2, 1)
    s.both("head", 1, 4, EYE_WHITE)
    s.both("head", 2, 4, eyes)
    s.paint("head", "front", 3, 8, shade(skin, -4), 2, 1)   # mouth, mostly behind the nose
    s.paint("head", "bottom", 0, 0, shade(skin, -2), 8, 8, grain=1)
    if nose:
        s.fill("nose", shade(skin, -1), grain=1)
        s.paint("nose", "top", 0, 0, skin, 2, 2)
        s.paint("nose", "bottom", 0, 0, shade(skin, -3), 2, 2)


def face_skin(s):
    """The skin colour of an already painted face (below the eyes, beside the nose)."""
    x, y, _, _ = face_rect("head", "front")
    return s.img.getpixel((x + 3, y + 6))[:3]


def cap(s, color, band, badge=None, top=None):
    """A peaked cap over hair rows 0-2: crown, band, dark visor at the front."""
    s.paint("head", "top", 0, 0, top or color, 8, 8, grain=2)
    s.ring("head", 0, color, 2, grain=2)
    s.ring("head", 2, band, 1, grain=1)
    s.paint("head", "front", 0, 2, (28, 28, 32), 8, 1, grain=1)
    s.paint("head", "front", 0, 3, shade(face_skin(s), -2), 8, 1)    # visor shadow over the brows
    if badge:
        s.paint("head", "front", 3, 1, badge, 2, 1)


def helmet(s, color, stripe=None):
    s.paint("head", "top", 0, 0, color, 8, 8, grain=2)
    s.paint("head", "top", 3, 0, shade(color, -2), 2, 8, grain=1)   # ridge
    s.ring("head", 0, color, 3, grain=2)
    if stripe:
        s.ring("head", 2, stripe, 1, grain=1)
    s.paint("head", "front", 0, 3, shade(color, -3), 8, 1, grain=1)   # brim shadow


# ---------- body ----------

def shirt(s, color, grain=3):
    s.fill("body", color, grain=grain)


def tie(s, color, knot=None):
    s.paint("body", "front", 3, 0, knot or shade(color, 1), 2, 1)
    s.paint("body", "front", 3, 1, color, 2, 6, grain=2)


def belt(s, color=(40, 36, 34), buckle=(180, 176, 168)):
    s.ring("body", 10, color, 1, grain=1)
    s.paint("body", "front", 3, 10, buckle, 2, 1)


def blazer(s, color, rows=14, v=4, lining=None, buttons=None):
    """Robe as a jacket: open V at the front showing the body for v rows."""
    s.ring("robe", 0, color, rows, grain=3)
    s.paint("robe", "top", 0, 0, color, 8, 6, grain=3)
    for y in range(v):
        half = 2 if y < v - 1 else 1
        s.paint("robe", "front", 4 - half, y, None, 2 * half, 1)
    s.both("robe", 2, 0, lining or shade(color, 2), 1, v - 1)      # lapels
    if buttons:
        for y in (v + 1, v + 4, v + 7):
            if y < rows:
                s.both("robe", 3, y, buttons)
    s.paint("robe", "front", 3, rows - 2, shade(color, -2), 2, 1)   # front edges meet


def vest(s, color, stripe, rows=11):
    """High-visibility vest on the robe, open at the front."""
    s.ring("robe", 0, color, rows, grain=3)
    s.paint("robe", "top", 0, 0, None, 8, 6)
    s.paint("robe", "top", 0, 0, color, 2, 6, grain=3)
    s.paint("robe", "top", 6, 0, color, 2, 6, grain=3)
    s.paint("robe", "front", 3, 0, None, 2, rows)
    for y in (5, 8):
        s.ring("robe", y, stripe, 1, grain=2)
        s.paint("robe", "front", 3, y, None, 2, 1)


# ---------- arms ----------

def sleeves(s, color, cuff=None, hands=SKIN, short=False, skin=SKIN):
    """Upper arms and the folded forearm bar. On the bar the elbows are at the
    ends and the hands meet in the middle."""
    for arm in ("arm_r", "arm_l"):
        s.fill(arm, color, grain=3)
        if short:
            s.ring(arm, 4, skin, 4, grain=1)
            s.paint(arm, "bottom", 0, 0, skin, 4, 4, grain=1)
    s.fill("bar", skin if short else color, grain=3 if not short else 1)
    for f in ("front", "top", "back", "bottom"):
        s.paint("bar", f, 3, 0, hands, 2, 4, grain=1)
        if cuff:
            s.paint("bar", f, 2, 0, cuff, 1, 4, grain=1)
            s.paint("bar", f, 5, 0, cuff, 1, 4, grain=1)
    # fingers of the top hand
    s.paint("bar", "front", 3, 1, shade(hands, -2), 1, 1)
    s.paint("bar", "front", 4, 2, shade(hands, -2), 1, 1)


# ---------- legs ----------

def trousers(s, color, shoe=SHOE, shoe_rows=2, grain=3):
    s.fill("leg", color, grain=grain)
    s.ring("leg", 12 - shoe_rows, shoe, shoe_rows, grain=1)
    s.paint("leg", "front", 0, 11 - shoe_rows, shade(color, -1), 4, 1)
    s.paint("leg", "bottom", 0, 0, shade(shoe, -1), 4, 4)


# ---------- characters ----------

def station_staff():
    """站務員: navy blazer, white shirt, cap with the company band, white gloves."""
    s = Skin(1)
    head(s, style="short")
    cap(s, NAVY, (92, 150, 210), badge=GOLD)
    shirt(s, WHITE_SHIRT)
    tie(s, (54, 92, 150))
    blazer(s, NAVY, rows=14, v=4, lining=shade(NAVY, 2), buttons=GOLD)
    sleeves(s, NAVY, cuff=WHITE_SHIRT, hands=(244, 244, 244))
    for f in ("right", "front", "back"):        # red armband on the right arm
        w, _ = s.face_size("arm_r", f)
        s.paint("arm_r", f, 0, 2, (196, 52, 48), w, 2, grain=1)
    trousers(s, NAVY)
    return s


def pilot():
    """機師 (Asuka Air): black double-breasted jacket, gold cuff stripes, cap."""
    s = Skin(2)
    head(s, style="cropped", hair=HAIR_BLACK)
    cap(s, BLACK_SUIT, GOLD, badge=GOLD, top=(242, 242, 242))
    shirt(s, WHITE_SHIRT)
    tie(s, BLACK_SUIT)
    blazer(s, BLACK_SUIT, rows=14, v=5, lining=shade(BLACK_SUIT, 2), buttons=GOLD)
    s.paint("robe", "front", 5, 6, GOLD, 2, 1)     # wings on the left chest
    sleeves(s, BLACK_SUIT, cuff=GOLD)
    trousers(s, BLACK_SUIT)
    return s


ASUKA_TEAL = (24, 104, 112)
ASUKA_CORAL = (232, 112, 84)


def flight_attendant():
    """空服員 (Asuka Air): teal jacket and skirt, coral scarf, hair in a bun."""
    s = Skin(3)
    head(s, style="bun", hair=HAIR_BROWN)
    shirt(s, WHITE_SHIRT)
    s.paint("body", "front", 2, 0, ASUKA_CORAL, 4, 2, grain=2)    # scarf knot
    s.paint("body", "front", 4, 2, ASUKA_CORAL, 1, 2, grain=2)
    blazer(s, ASUKA_TEAL, rows=16, v=3, lining=shade(ASUKA_TEAL, 2))
    s.ring("robe", 12, shade(ASUKA_TEAL, -1), 4, grain=3)          # skirt to the knee
    s.paint("robe", "front", 3, 12, shade(ASUKA_TEAL, -1), 2, 4, grain=3)
    s.paint("robe", "front", 3, 15, shade(ASUKA_TEAL, -3), 2, 1)   # pleat
    sleeves(s, ASUKA_TEAL, cuff=ASUKA_CORAL)
    trousers(s, (222, 186, 156), shoe=(30, 28, 30), shoe_rows=1, grain=1)   # stockings
    return s


def cleanroom():
    """晶圓廠 (無塵室): white coverall with hood and mask, goggles, blue gloves."""
    s = Skin(4)
    suit, crease = (238, 240, 244), (214, 218, 226)
    head(s, nose=False, brows=False)
    s.fill("head", suit, grain=2)
    s.ring("head", 3, (70, 80, 96), 3, grain=1)        # goggle band
    s.paint("head", "front", 1, 3, (150, 170, 190), 6, 3, grain=1)
    s.paint("head", "front", 1, 4, SKIN, 6, 1)
    s.both("head", 2, 4, EYE)
    s.paint("head", "front", 1, 6, (226, 230, 236), 6, 4, grain=1)   # mask
    s.paint("head", "front", 2, 8, crease, 4, 1)
    shirt(s, suit)
    s.paint("body", "front", 4, 0, crease, 1, 12)      # zip
    s.ring("robe", 0, suit, 18, grain=2)               # loose coverall
    s.paint("robe", "top", 0, 0, suit, 8, 6, grain=2)
    s.paint("robe", "front", 4, 0, crease, 1, 18)
    s.paint("robe", "front", 6, 2, (80, 140, 200), 1, 2)    # badge
    for side in ("right", "left"):
        s.paint("robe", side, 0, 13, crease, 6, 1)
    sleeves(s, suit, cuff=crease, hands=(120, 150, 222))
    trousers(s, suit, shoe=(200, 214, 236), shoe_rows=4, grain=2)   # boot covers
    return s


def construction_worker():
    """工地工人 (Asuka Inc. 的工地): white helmet, grey work clothes, lime vest."""
    s = Skin(5)
    head(s, skin=SKIN_TAN, style="short")
    helmet(s, (240, 240, 236), stripe=(52, 110, 180))
    work = (110, 116, 124)
    shirt(s, work)
    belt(s)
    vest(s, (188, 228, 52), (226, 230, 232), rows=11)
    sleeves(s, work, cuff=shade(work, -2), hands=(214, 196, 150))   # cotton gloves
    trousers(s, work, shoe=(52, 46, 40), shoe_rows=3)
    return s


def doctor():
    """醫師: knee-length white coat over light blue scrubs."""
    s = Skin(6)
    head(s, style="short", hair=HAIR_GREY)
    frame = (70, 72, 80)                               # glasses
    s.both("head", 0, 4, frame)
    s.both("head", 1, 3, frame, 2, 1)
    s.both("head", 1, 5, frame, 2, 1)
    s.paint("head", "front", 3, 4, frame, 2, 1)
    s.paint("head", "right", 6, 4, frame, 2, 1)
    s.paint("head", "left", 0, 4, frame, 2, 1)
    scrubs = (118, 168, 200)
    shirt(s, scrubs)
    s.paint("body", "front", 3, 0, shade(scrubs, -3), 2, 2)
    coat = (240, 242, 244)
    blazer(s, coat, rows=18, v=4, lining=(222, 226, 230))
    s.paint("robe", "front", 3, 14, None, 2, 4)          # slit
    s.paint("robe", "front", 5, 9, (210, 214, 220), 2, 2)     # pocket
    s.paint("robe", "front", 6, 3, (80, 84, 92), 1, 3)        # pen
    s.paint("body", "front", 2, 1, (70, 74, 82), 1, 4)       # stethoscope
    s.paint("body", "front", 5, 1, (70, 74, 82), 1, 4)
    sleeves(s, coat, cuff=scrubs)
    trousers(s, scrubs, shoe=(236, 236, 236))
    return s


def tourist():
    """觀光客: sun cap, T-shirt, backpack, jeans, sneakers, a camera in hand."""
    s = Skin(7)
    head(s, style="bob", hair=HAIR_BROWN)
    cap(s, (236, 224, 196), (236, 224, 196), top=(236, 224, 196))
    s.paint("head", "front", 0, 2, (200, 186, 156), 8, 1)
    tee = (240, 180, 70)
    shirt(s, tee)
    s.paint("body", "front", 2, 0, shade(tee, -3), 4, 1)
    # backpack: robe back panel only, straps over the shoulders
    pack = (60, 120, 96)
    s.paint("robe", "back", 1, 1, pack, 6, 9, grain=3)
    s.paint("robe", "back", 2, 3, shade(pack, -2), 4, 3, grain=2)
    s.paint("robe", "top", 1, 0, pack, 1, 6)
    s.paint("robe", "top", 6, 0, pack, 1, 6)
    s.both("robe", 1, 0, pack, 1, 6)
    sleeves(s, tee, short=True)
    s.paint("bar", "front", 3, 0, (40, 40, 44), 2, 3)     # camera
    s.paint("bar", "top", 3, 0, (40, 40, 44), 2, 3)
    s.paint("bar", "front", 3, 1, (120, 160, 200), 1, 1)  # lens
    trousers(s, (70, 100, 150), shoe=(236, 236, 232))
    s.paint("leg", "front", 1, 3, (90, 120, 168), 2, 1)
    return s


CHARACTERS = {
    "station_staff": ("站務員", station_staff),
    "pilot": ("機師", pilot),
    "flight_attendant": ("空服員", flight_attendant),
    "cleanroom": ("晶圓廠無塵衣", cleanroom),
    "construction_worker": ("工地工人", construction_worker),
    "doctor": ("醫師", doctor),
    "tourist": ("觀光客", tourist),
}


# ---------- preview geometry ----------

def box_faces(box):
    u, v, w, h, d = BOXES[box]

    def f(x, y, a, b):
        return {"uv": [x, y], "uv_size": [a, b]}
    # The top is flipped so that its bottom edge meets the front, as in a skin net.
    return {"up": f(u + d + w, v + d, -w, -d), "down": f(u + d + w, v, w, d),
            "east": f(u, v + d, d, h), "north": f(u + d, v + d, w, h),
            "west": f(u + d + w, v + d, d, h), "south": f(u + 2 * d + w, v + d, w, h)}


def cube(box, origin, size, inflate=0.0, **extra):
    c = {"origin": [a - inflate for a in origin], "size": [a + 2 * inflate for a in size],
         "uv": box_faces(box)}
    c.update(extra)
    return c


# Folded arms: the vanilla animation moves the arms 1 down and 1 forward and
# tilts them 43 degrees forward around the shoulders.
ARMS = {"rotation": [42.97, 0, 0], "pivot": [0, 21, -1]}
PREVIEW_GEO = {"format_version": "1.12.0", "minecraft:geometry": [{
    "description": {"identifier": "geometry.npc_preview", "texture_width": 64, "texture_height": 64},
    "bones": [
        {"name": "head", "pivot": [0, 24, 0], "cubes": [
            cube("head", [-4, 24, -4], [8, 10, 8]), cube("nose", [-1, 23, -6], [2, 4, 2])]},
        {"name": "body", "pivot": [0, 24, 0], "cubes": [
            cube("body", [-4, 12, -3], [8, 12, 6]), cube("robe", [-4, 6, -3], [8, 18, 6], 0.5),
            cube("jacket", [-4, 12, -2], [8, 12, 4], 0.25)]},
        {"name": "arms", "pivot": [0, 21, -1], "cubes": [
            cube("bar", [-4, 15, -3], [8, 4, 4], **ARMS),
            cube("arm_r", [4, 15, -3], [4, 8, 4], **ARMS),
            cube("arm_l", [-8, 15, -3], [4, 8, 4], **ARMS)]},
        {"name": "legs", "pivot": [0, 12, 0], "cubes": [
            cube("leg", [0, 0, -2], [4, 12, 4]), cube("leg", [-4, 0, -2], [4, 12, 4])]},
    ]}]}


# ---------- preview sheets ----------

def npc(name, x=0, z=0, turn=0):
    """An NPC standing on y = 0, facing +z (towards the default camera) when turn = 0."""
    return {"type": "geo", "geo": f"{REL}/npc_preview.geo.json", "texture": f"{REL}/skins/{name}.png",
            "position": [x, 0, z], "rotationY": 180 + turn}


def block(x, y, z, color, size=(16, 16, 16)):
    """A coloured box with its lower north-west corner at (x, y, z)."""
    return {"type": "block", "origin": [x, y, z], "size": list(size), "color": color}


def lit(c):
    """An RGB colour as the hex string the preview tool takes for blocks."""
    return "#%02x%02x%02x" % c


def floor(x0, x1, z0, z1, a, b):
    return [block(x, -16, z, lit(a if ((x + z) // 16) % 2 == 0 else b))
            for x in range(x0, x1, 16) for z in range(z0, z1, 16)]


def lineup():
    names = list(CHARACTERS)
    panels = []
    for az, side in ((20, "正面"), (200, "背面")):
        for n in names:
            panels.append({"label": f"{CHARACTERS[n][0]}（{side}）",
                           "camera": {"azimuth": az, "elevation": 10, "size": 42, "target": [0, 17, 0]},
                           "objects": [npc(n)]})
    return {"title": "NPC 皮膚草稿（第一輪：風格樣本，人物與格子待決定）", "columns": len(names),
            "panelWidth": 200, "panelHeight": 290, "background": "#e8edf1", "panels": panels}


def station_scene():
    objs = floor(-80, 96, -48, 32, (196, 198, 200), (184, 186, 190))
    wall = (236, 236, 232)
    for x in range(-80, 96, 16):
        for y in (0, 16, 32):
            objs.append(block(x, y, -64, lit(wall)))
        objs.append(block(x, 48, -64, lit((38, 50, 82))))
    objs.append(block(-40, 24, -48, lit((30, 40, 70)), (64, 12, 2)))       # departure board
    objs.append(block(-36, 28, -46.5, lit((230, 180, 60)), (24, 2, 1)))
    objs.append(block(-36, 32, -46.5, lit((240, 240, 240)), (40, 2, 1)))
    for gx in (-8, 24, 56):                                                   # ticket gates
        objs.append(block(gx, 0, -36, lit((214, 218, 222)), (6, 15, 28)))
        objs.append(block(gx, 15, -36, lit((60, 120, 190)), (6, 1, 10)))
    objs += [npc("station_staff", -40, -10, 20), npc("tourist", 40, 0, -30)]
    return {"label": "車站的剪票口：站務員與觀光客",
            "camera": {"azimuth": 18, "elevation": 16, "size": 92, "target": [8, 22, -16]}, "objects": objs}


def airport_scene():
    objs = floor(-96, 96, -48, 32, (226, 228, 230), (214, 216, 220))
    for x in range(-96, 96, 16):
        for y in (0, 16, 32, 48):
            c = ASUKA_TEAL if y == 32 else (240, 240, 238)
            objs.append(block(x, y, -64, lit(c)))
    objs.append(block(-64, 34, -48, lit((250, 250, 250)), (40, 8, 1)))       # Asuka Air sign
    objs.append(block(-60, 36, -47, lit(ASUKA_CORAL), (6, 4, 1)))
    for x in range(-80, 48, 16):                                              # check-in counter
        objs.append(block(x, 0, -36, lit((244, 244, 242)), (16, 14, 12)))
        objs.append(block(x, 14, -36, lit((70, 74, 80)), (16, 2, 12)))
    objs += [npc("pilot", -40, 0, 15), npc("flight_attendant", -10, 0, -10), npc("tourist", 52, 4, -40)]
    objs.append(block(64, 0, 0, lit((60, 64, 72)), (8, 12, 5)))              # suitcase
    return {"label": "機場的報到櫃台：Asuka Air 的機師與空服員（顏色是暫定的）",
            "camera": {"azimuth": 15, "elevation": 16, "size": 94, "target": [-4, 24, -16]}, "objects": objs}


def fab_scene():
    objs = floor(-80, 96, -48, 32, (236, 236, 228), (228, 228, 220))
    for x in range(-80, 96, 16):
        for y in (0, 16, 32, 48):
            objs.append(block(x, y, -64, lit((246, 240, 200))))
    for x, w in ((-72, 40), (8, 56)):                                         # tools
        objs.append(block(x, 0, -56, lit((232, 234, 236)), (w, 30, 20)))
        objs.append(block(x + 4, 18, -36, lit((60, 70, 84)), (12, 8, 1)))
        objs.append(block(x + 20, 22, -36, lit((240, 200, 70)), (4, 2, 1)))
    objs += [npc("cleanroom", -20, -10, 10), npc("construction_worker", 56, 8, -20)]
    return {"label": "晶圓廠的無塵室（黃光區）；右邊借放工地工人比較顏色",
            "camera": {"azimuth": 18, "elevation": 16, "size": 92, "target": [8, 22, -16]}, "objects": objs}


def nose_scene():
    no_nose = dict(npc("station_staff", 14, 0, 0), texture=f"{REL}/compare_no_nose.png")
    objs = [npc("station_staff", -14, 0, 0), no_nose]
    return {"label": "鼻子：原版 NPC 的鼻子保留（左）或拿掉（右）",
            "camera": {"azimuth": 20, "elevation": 6, "size": 44, "target": [0, 20, 0]}, "objects": objs}


def scenes():
    return {"title": "NPC 皮膚草稿：放進情境", "columns": 2, "panelWidth": 620, "panelHeight": 400,
            "background": "#e8edf1",
            "panels": [station_scene(), airport_scene(), fab_scene(), nose_scene()]}


if __name__ == "__main__":
    for name, (_, make) in CHARACTERS.items():
        make().save(name)
    # the nose comparison: the station staff without the nose
    s = station_staff()
    s.paint("nose", "top", 0, 0, None, 2, 2)
    s.paint("nose", "bottom", 0, 0, None, 2, 2)
    for f in SIDES:
        s.paint("nose", f, 0, 0, None, 2, 4)
    s.img.save(HERE / "compare_no_nose.png")
    (HERE / "npc_preview.geo.json").write_text(json.dumps(PREVIEW_GEO, indent=1) + "\n", encoding="utf-8")
    (HERE / "preview.json").write_text(json.dumps(lineup(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "scene.json").write_text(json.dumps(scenes(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(CHARACTERS)} skins, compare_no_nose.png, npc_preview.geo.json, preview.json, scene.json")
