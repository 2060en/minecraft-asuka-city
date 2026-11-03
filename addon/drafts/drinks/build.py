"""Build the drinks draft: 20 potion icons become drinks for the shop shelves.

Run from the repository root:
    python3 addon/drafts/drinks/build.py

Resource pack only. Bedrock gives every potion effect its own item icon
(textures/items/potion_bottle_<effect>.png), so each drinkable potion can
become a different drink; the long and strong versions share the icon of
their effect. Splash and lingering potions keep the vanilla look. In a
(glow) item frame or on a shelf the icon is what shows. The author asked for
20 drinks, designed by Claude (2026-11-03); the ones chosen are those the
creative inventory has, so every drink is easy to get.

The names can follow through the language files (potion.<effect>.name),
which do not touch the effect names shown while it is active.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

OUT = (40, 42, 46)          # outline
GLASS = (206, 226, 236)
GLASS_HI = (240, 248, 252)
SILVER = (196, 200, 206)
SILVER_LO = (150, 155, 162)


def new():
    return Image.new("RGBA", (16, 16), (0, 0, 0, 0))


def rect(px, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px[x, y] = c + (255,)


def outline(img):
    px = img.load()
    edge = []
    for y in range(16):
        for x in range(16):
            if px[x, y][3] == 0 and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and px[x + dx, y + dy][3]
                                        and px[x + dx, y + dy][:3] != OUT
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                edge.append((x, y))
    for x, y in edge:
        px[x, y] = OUT + (255,)
    return img


def shade(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


def can(body, band=None, mark=None, tall=False):
    """An aluminium can: silver lid, coloured body, an optional band."""
    img = new()
    px = img.load()
    top = 1 if tall else 3
    rect(px, 5, top, 10, top, SILVER)
    rect(px, 5, top + 1, 10, 14, body)
    rect(px, 9, top + 1, 10, 14, shade(body, -28))          # the shaded side
    rect(px, 5, 14, 10, 14, SILVER_LO)
    px[6, top] = SILVER_LO + (255,)                          # the tab
    if band:
        y = (top + 14) // 2
        rect(px, 5, y, 10, y + 1, band)
        rect(px, 9, y, 10, y + 1, shade(band, -28))
    if mark:
        px[6, (top + 14) // 2 + 3] = mark + (255,)
        px[7, (top + 14) // 2 + 3] = mark + (255,)
    return outline(img)


def pet(liquid, cap, label, label2=None, dots=None, bubbles=False):
    """A plastic bottle: cap, neck, shoulder, a label round the middle."""
    img = new()
    px = img.load()
    rect(px, 7, 1, 8, 1, cap)                                 # cap
    rect(px, 7, 2, 8, 3, GLASS)                               # neck
    rect(px, 6, 4, 9, 4, GLASS)                               # shoulder
    rect(px, 5, 5, 10, 14, liquid)
    rect(px, 10, 5, 10, 14, shade(liquid, -24))
    px[6, 6] = GLASS_HI + (255,)
    rect(px, 5, 8, 10, 11, label)                             # label
    rect(px, 10, 8, 10, 11, shade(label, -24))
    if label2:
        rect(px, 6, 9, 8, 9, label2)
    if dots:
        for x, y in ((6, 6), (9, 7), (7, 12), (9, 13), (6, 13)):
            px[x, y] = dots + (255,)
    if bubbles:
        for x, y in ((7, 6), (8, 13), (6, 12), (9, 6)):
            px[x, y] = GLASS_HI + (255,)
    return outline(img)


def carton(body, side, mark=None, straw=None):
    """A drink box with a straw on top."""
    img = new()
    px = img.load()
    rect(px, 4, 5, 9, 14, body)
    rect(px, 10, 5, 11, 14, side)
    rect(px, 4, 4, 11, 4, shade(body, 18))
    if straw:
        rect(px, 9, 1, 9, 3, straw)
        px[10, 1] = straw + (255,)
    if mark:
        rect(px, 5, 8, 8, 11, mark)
    return outline(img)


def ramune():
    """A glass soda bottle with a marble in its neck."""
    img = new()
    px = img.load()
    g, gd = (120, 196, 202), (90, 160, 170)
    rect(px, 7, 1, 8, 1, (70, 120, 200))                     # blue cap ring
    rect(px, 7, 2, 8, 4, g)
    rect(px, 6, 3, 9, 3, g)                                   # the pinched neck
    px[7, 3] = GLASS_HI + (255,)                              # the marble
    px[8, 3] = GLASS_HI + (255,)
    rect(px, 6, 5, 9, 5, g)
    rect(px, 5, 6, 10, 14, g)
    rect(px, 10, 6, 10, 14, gd)
    rect(px, 5, 9, 10, 11, (236, 240, 244))                  # label
    rect(px, 6, 10, 9, 10, (70, 120, 200))
    return outline(img)


def bubble_tea():
    """A plastic cup with a sealed top, a fat straw and tapioca at the bottom."""
    img = new()
    px = img.load()
    tea = (200, 160, 112)
    rect(px, 4, 4, 11, 4, (236, 238, 240))                   # sealed film
    for y in range(5, 15):
        a, b = 4 + (y - 5) // 5, 11 - (y - 5) // 5
        rect(px, a, y, b, y, tea)
        px[b, y] = shade(tea, -24) + (255,)
    for x, y in ((5, 13), (7, 13), (9, 13), (6, 12), (8, 12), (10, 12), (6, 14), (8, 14)):
        px[x, y] = (52, 34, 26, 255)                          # tapioca pearls
    rect(px, 8, 0, 9, 3, (230, 90, 120))                      # straw
    return outline(img)


def water():
    img = pet((196, 224, 244), (60, 120, 200), (90, 160, 220), (236, 244, 250))
    return img


DRINKS = [   # (texture name, zh_TW, en_US, icon)
    ("drinkable", "礦泉水", "Mineral Water", water),
    ("nightVision", "罐裝黑咖啡", "Black Coffee", lambda: can((52, 36, 28), (196, 160, 82))),
    ("invisibility", "運動飲料", "Sports Drink", lambda: pet((226, 236, 244), (236, 240, 244), (54, 96, 190), (236, 240, 244))),
    ("jump", "彈珠汽水", "Ramune", ramune),
    ("fireResistance", "可樂", "Cola", lambda: can((196, 32, 38), (240, 240, 240))),
    ("moveSpeed", "能量飲料", "Energy Drink", lambda: can((40, 60, 140), (196, 200, 206), tall=True)),
    ("moveSlowdown", "奶茶", "Milk Tea", lambda: pet((214, 180, 140), (196, 60, 50), (150, 100, 70), (236, 220, 196))),
    ("waterBreathing", "綠茶", "Green Tea", lambda: pet((150, 182, 90), (40, 120, 60), (230, 236, 220), (60, 130, 70))),
    ("heal", "柳橙汁", "Orange Juice", lambda: pet((240, 150, 40), (240, 150, 40), (250, 230, 120), (240, 120, 30))),
    ("harm", "啤酒", "Beer", lambda: can((222, 186, 70), (240, 240, 236), (180, 40, 40))),
    ("poison", "蘋果西打", "Apple Soda", lambda: can((220, 210, 80), (60, 150, 70), (200, 40, 40))),
    ("regeneration", "草莓牛奶", "Strawberry Milk", lambda: carton((246, 170, 190), (226, 146, 168), (236, 90, 110), (240, 240, 240))),
    ("damageBoost", "番茄汁", "Tomato Juice", lambda: can((200, 40, 36), (80, 150, 60))),
    ("weakness", "豆漿", "Soy Milk", lambda: carton((236, 222, 190), (214, 198, 164), (170, 140, 80), (240, 240, 240))),
    ("wither", "珍珠奶茶", "Bubble Tea", bubble_tea),
    ("turtleMaster", "烏龍茶", "Oolong Tea", lambda: pet((176, 110, 50), (150, 40, 40), (236, 226, 206), (150, 40, 40))),
    ("slowFall", "檸檬紅茶", "Lemon Tea", lambda: carton((246, 214, 70), (222, 188, 50), (190, 90, 40), (240, 240, 240))),
    ("windCharged", "氣泡水", "Sparkling Water", lambda: pet((214, 236, 230), (60, 160, 110), (236, 246, 242), (60, 160, 110), bubbles=True)),
    ("weaving", "乳酸飲料", "Yogurt Soda", lambda: pet((240, 242, 244), (60, 110, 200), (240, 242, 244), dots=(80, 130, 220))),
    ("oozing", "葡萄汁", "Grape Juice", lambda: pet((110, 50, 120), (110, 50, 120), (200, 170, 210), (90, 40, 100))),
]

if __name__ == "__main__":
    icons = HERE / "icons"
    icons.mkdir(exist_ok=True)
    for name, _, _, draw in DRINKS:
        draw().save(icons / f"potion_bottle_{name}.png")

    # flat preview: every icon at 8x with its name, and a row in a shop fridge
    font_path = next((p for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                                  "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                                  "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc") if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
    cols, cell = 5, 190
    sheet = Image.new("RGBA", (cols * cell, 4 * cell + 60), (232, 237, 241, 255))
    d = ImageDraw.Draw(sheet)
    d.text((20, 16), "20 種飲料：藥水換圖示（草稿）", fill=(40, 42, 46), font=font)
    for i, (name, zh, en, _) in enumerate(DRINKS):
        x, y = (i % cols) * cell, (i // cols) * cell + 60
        icon = Image.open(icons / f"potion_bottle_{name}.png").resize((128, 128), Image.NEAREST)
        sheet.alpha_composite(icon, (x + 31, y))
        d.text((x + 95 - d.textlength(zh, font=font) / 2, y + 132), zh, fill=(40, 42, 46), font=font)
        d.text((x + 95 - d.textlength(name, font=font) / 2, y + 156), name, fill=(120, 124, 130), font=font)
    sheet.save(HERE / "preview.png")
    print(f"wrote {len(DRINKS)} icons and preview.png")
