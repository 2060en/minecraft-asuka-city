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

The names follow through the language files: zh_TW.lang and en_US.lang
here hold the potion.<effect>.name lines (the effect names shown while it is
active stay). The strong version shows "II" after the name.

Second version (author, 2026-11-03): no hand-shaken drinks for now (the
bubble tea went, coconut water took its potion), no straws on the drink
boxes, and everything drawn wider and to the full height of the 16 x 16
icon, so that it looks bigger in an item frame or on a shelf, where the game
shows the whole icon at a fixed size.
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
    """An aluminium can, 8 pixels wide: silver lid, coloured body, an optional band."""
    img = new()
    px = img.load()
    top = 1 if tall else 3
    rect(px, 4, top, 11, top, SILVER)
    rect(px, 4, top + 1, 11, 14, body)
    rect(px, 10, top + 1, 11, 14, shade(body, -28))         # the shaded side
    rect(px, 4, 14, 11, 14, SILVER_LO)
    rect(px, 5, top, 6, top, SILVER_LO)                       # the tab
    mid = (top + 14) // 2
    if band:
        rect(px, 4, mid, 11, mid + 1, band)
        rect(px, 10, mid, 11, mid + 1, shade(band, -28))
    if mark:
        rect(px, 6, mid + 3, 7, mid + 4, mark)
    return outline(img)


def pet(liquid, cap, label, label2=None, dots=None, bubbles=False):
    """A plastic bottle, 8 pixels wide: cap, neck, shoulder, a label round the middle."""
    img = new()
    px = img.load()
    rect(px, 6, 0, 9, 0, cap)                                 # cap
    rect(px, 6, 1, 9, 1, shade(cap, -30))
    rect(px, 6, 2, 9, 2, GLASS)                               # neck
    rect(px, 5, 3, 10, 3, GLASS)                              # shoulder
    rect(px, 4, 4, 11, 14, liquid)
    rect(px, 11, 4, 11, 14, shade(liquid, -24))
    rect(px, 5, 5, 5, 6, GLASS_HI)
    rect(px, 4, 7, 11, 11, label)                             # label
    rect(px, 11, 7, 11, 11, shade(label, -24))
    if label2:
        rect(px, 5, 9, 9, 9, label2)
    if dots:
        for x, y in ((5, 5), (9, 6), (6, 12), (10, 13), (5, 13), (8, 5)):
            px[x, y] = dots + (255,)
    if bubbles:
        for x, y in ((7, 5), (9, 13), (6, 12), (10, 5), (7, 13)):
            px[x, y] = GLASS_HI + (255,)
    return outline(img)


def carton(body, side, mark=None):
    """A drink box (no straw, author 2026-11-03), 10 pixels wide."""
    img = new()
    px = img.load()
    rect(px, 3, 2, 10, 14, body)
    rect(px, 11, 2, 12, 14, side)
    rect(px, 3, 2, 12, 2, shade(body, 20))                    # the sealed top edge
    if mark:
        rect(px, 4, 7, 9, 11, mark)
    return outline(img)


def ramune():
    """A glass soda bottle with a marble in its neck, 8 pixels wide."""
    img = new()
    px = img.load()
    g, gd = (120, 196, 202), (90, 160, 170)
    rect(px, 6, 0, 9, 0, (70, 120, 200))                     # blue cap ring
    rect(px, 6, 1, 9, 3, g)
    rect(px, 5, 2, 10, 2, g)                                  # the pinched neck
    rect(px, 7, 2, 8, 2, GLASS_HI)                            # the marble
    rect(px, 5, 4, 10, 4, g)
    rect(px, 4, 5, 11, 14, g)
    rect(px, 11, 5, 11, 14, gd)
    rect(px, 4, 8, 11, 11, (236, 240, 244))                  # label
    rect(px, 5, 9, 10, 10, (70, 120, 200))
    return outline(img)


def water():
    return pet((196, 224, 244), (60, 120, 200), (90, 160, 220), (236, 244, 250))


# (texture, language keys, zh_TW, en_US, icon); the long and strong versions
# share the key of their effect, and all the base potions are mineral water.
DRINKS = [
    ("drinkable", ["emptyPotion", "awkward", "mundane", "mundane.extended", "thick"], "礦泉水", "Mineral Water", water),
    ("nightVision", ["nightVision"], "罐裝黑咖啡", "Black Coffee", lambda: can((52, 36, 28), (196, 160, 82))),
    ("invisibility", ["invisibility"], "運動飲料", "Sports Drink", lambda: pet((226, 236, 244), (236, 240, 244), (54, 96, 190), (236, 240, 244))),
    ("jump", ["jump"], "彈珠汽水", "Ramune", ramune),
    ("fireResistance", ["fireResistance"], "可樂", "Cola", lambda: can((196, 32, 38), (240, 240, 240))),
    ("moveSpeed", ["moveSpeed"], "能量飲料", "Energy Drink", lambda: can((40, 60, 140), (196, 200, 206), tall=True)),
    ("moveSlowdown", ["moveSlowdown"], "奶茶", "Milk Tea", lambda: pet((214, 180, 140), (196, 60, 50), (150, 100, 70), (236, 220, 196))),
    ("waterBreathing", ["waterBreathing"], "綠茶", "Green Tea", lambda: pet((150, 182, 90), (40, 120, 60), (230, 236, 220), (60, 130, 70))),
    ("heal", ["heal"], "柳橙汁", "Orange Juice", lambda: pet((240, 150, 40), (240, 150, 40), (250, 230, 120), (240, 120, 30))),
    ("harm", ["harm"], "啤酒", "Beer", lambda: can((222, 186, 70), (240, 240, 236), (180, 40, 40))),
    ("poison", ["poison"], "蘋果西打", "Apple Soda", lambda: can((220, 210, 80), (60, 150, 70), (200, 40, 40))),
    ("regeneration", ["regeneration"], "草莓牛奶", "Strawberry Milk", lambda: carton((246, 170, 190), (226, 146, 168), (236, 90, 110))),
    ("damageBoost", ["damageBoost"], "番茄汁", "Tomato Juice", lambda: can((200, 40, 36), (80, 150, 60))),
    ("weakness", ["weakness"], "豆漿", "Soy Milk", lambda: carton((236, 222, 190), (214, 198, 164), (170, 140, 80))),
    ("wither", ["wither"], "椰子水", "Coconut Water", lambda: carton((240, 244, 236), (214, 220, 208), (90, 150, 80))),
    ("turtleMaster", ["turtleMaster"], "烏龍茶", "Oolong Tea", lambda: pet((176, 110, 50), (150, 40, 40), (236, 226, 206), (150, 40, 40))),
    ("slowFall", ["slowFalling"], "檸檬紅茶", "Lemon Tea", lambda: carton((246, 214, 70), (222, 188, 50), (190, 90, 40))),
    ("windCharged", ["windCharged"], "氣泡水", "Sparkling Water", lambda: pet((214, 236, 230), (60, 160, 110), (236, 246, 242), (60, 160, 110), bubbles=True)),
    ("weaving", ["weaving"], "乳酸飲料", "Yogurt Soda", lambda: pet((240, 242, 244), (60, 110, 200), (240, 242, 244), dots=(80, 130, 220))),
    ("oozing", ["oozing"], "葡萄汁", "Grape Juice", lambda: pet((110, 50, 120), (110, 50, 120), (200, 170, 210), (90, 40, 100))),
]


def lang_lines(lang):
    """potion.<key>.name lines for zh_TW or en_US."""
    i = 2 if lang == "zh_TW" else 3
    return [f"potion.{key}.name={d[i]}" for d in DRINKS for key in d[1]]


if __name__ == "__main__":
    icons = HERE / "icons"
    icons.mkdir(exist_ok=True)
    for old in icons.glob("*.png"):
        old.unlink()
    for name, _, _, _, draw in DRINKS:
        draw().save(icons / f"potion_bottle_{name}.png")
    for lang in ("zh_TW", "en_US"):
        (HERE / f"{lang}.lang").write_text("\n".join(lang_lines(lang)) + "\n", encoding="utf-8")

    # flat preview: every icon at 8x with its name, and a row in a shop fridge
    font_path = next((p for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                                  "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                                  "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc") if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
    cols, cell = 5, 190
    sheet = Image.new("RGBA", (cols * cell, 4 * cell + 60), (232, 237, 241, 255))
    d = ImageDraw.Draw(sheet)
    d.text((20, 16), "20 種飲料：藥水換圖示（草稿）", fill=(40, 42, 46), font=font)
    for i, (name, _, zh, en, _) in enumerate(DRINKS):
        x, y = (i % cols) * cell, (i // cols) * cell + 60
        icon = Image.open(icons / f"potion_bottle_{name}.png").resize((128, 128), Image.NEAREST)
        sheet.alpha_composite(icon, (x + 31, y))
        d.text((x + 95 - d.textlength(zh, font=font) / 2, y + 132), zh, fill=(40, 42, 46), font=font)
        d.text((x + 95 - d.textlength(en, font=font) / 2, y + 156), en, fill=(120, 124, 130), font=font)
    sheet.save(HERE / "preview.png")
    print(f"wrote {len(DRINKS)} icons and preview.png")
