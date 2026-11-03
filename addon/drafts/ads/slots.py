"""Draw the painting slot sheet: every painting that can be replaced, as an
empty box at its real proportions, with its slot code and vanilla name.

Run from the repository root:
    python3 addon/drafts/ads/slots.py

The slot list is the one in docs/ads.md; keep the two in step.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# (size label, width, height, [(code, vanilla name, note)])
GROUPS = [
    ("2 × 1", 2, 1, [("A1", "Pool", ""), ("A2", "Courbet", ""), ("A3", "Sea", ""), ("A4", "Sunset", ""), ("A5", "Creebet", "")]),
    ("1 × 2", 1, 2, [("B1", "Wanderer", ""), ("B2", "Graham", ""), ("B3", "prairie_ride", "")]),
    ("2 × 2", 2, 2, [("C1", "Match", ""), ("C2", "Bust", ""), ("C3", "Stage", ""), ("C4", "Void", ""),
                     ("C5", "SkullAndRoses", ""), ("C6", "Wither", ""), ("C7", "baroque", ""), ("C8", "humble", "")]),
    ("3 × 3", 3, 3, [("D1", "bouquet", ""), ("D2", "cavebird", ""), ("D3", "cotan", ""), ("D4", "endboss", ""),
                     ("D5", "fern", ""), ("D6", "owlemons", ""), ("D7", "sunflowers", ""), ("D8", "tides", "")]),
    ("4 × 2", 4, 2, [("E1", "Fighters", ""), ("E2", "changing", ""), ("E3", "finding", ""), ("E4", "lowmist", ""), ("E5", "passage", "")]),
    ("3 × 4", 3, 4, [("F1", "backyard", ""), ("F2", "pond", "")]),
    ("4 × 3", 4, 3, [("G1", "Skeleton", ""), ("G2", "DonkeyKong", "")]),
    ("4 × 4", 4, 4, [("H1", "Pointer", ""), ("H2", "Pigscene", ""), ("H3", "BurningSkull", ""), ("H4", "orb", ""), ("H5", "unpacked", "")]),
    ("2 × 2（只能靠改存檔放）", 2, 2, [("X1", "Earth", ""), ("X2", "Wind", ""), ("X3", "Fire", ""), ("X4", "Water", "")]),
    ("1 × 1", 1, 1, [("S1", "Kebab", "筆電：桌面"), ("S2", "Aztec", "筆電：寫程式"), ("S3", "Alban", ""), ("S4", "Aztec2", ""),
                     ("S5", "Bomb", ""), ("S6", "Plant", ""), ("S7", "Wasteland", ""), ("S8", "meditative", "")]),
]

UNIT = 34          # pixels per block
GAP = 16
MARGIN = 24
WIDTH = 1500

title_font = ImageFont.truetype(FONT, 30)
head_font = ImageFont.truetype(FONT, 22)
code_font = ImageFont.truetype(FONT, 20)
name_font = ImageFont.truetype(FONT, 13)

# Lay out first to know the height.
layout = []
y = MARGIN + 50
for label, w, h, slots in GROUPS:
    y += 34
    x = MARGIN
    row_h = 0
    for slot in slots:
        bw, bh = w * UNIT, h * UNIT
        if x + bw > WIDTH - MARGIN:
            x = MARGIN
            y += row_h + GAP + 18
            row_h = 0
        layout.append((label, x, y, bw, bh, slot))
        x += max(bw, 96) + GAP
        row_h = max(row_h, bh)
    y += row_h + GAP + 40

img = Image.new("RGB", (WIDTH, y + MARGIN), (246, 247, 249))
d = ImageDraw.Draw(img)
d.text((MARGIN, MARGIN), "可以換成廣告的畫：每一格的編號（框的大小照實際比例，1 格 = 1 方塊）", font=title_font, fill=(30, 30, 30))
seen = set()
for label, x, y0, bw, bh, (code, name, note) in layout:
    if label not in seen:
        seen.add(label)
        d.text((MARGIN, y0 - 32), label, font=head_font, fill=(60, 60, 60))
    used = bool(note)
    fill = (226, 232, 240) if used else (255, 255, 255)
    d.rectangle([x, y0, x + bw, y0 + bh], fill=fill, outline=(120, 128, 136), width=2)
    d.text((x + 6, y0 + 4), code, font=code_font, fill=(20, 60, 120))
    d.text((x, y0 + bh + 3), name, font=name_font, fill=(90, 90, 90))
    if note:
        d.text((x, y0 + bh + 19), note, font=name_font, fill=(20, 60, 120))
img.save(HERE / "slots.png")
print("wrote slots.png")
