"""Draw a contact sheet of the 60 vanilla NPC skins, numbered N01-N60.

Run from the repository root:
    python3 addon/drafts/npc/vanilla_sheet.py [out.png]

Downloads the skins from Mojang's official bedrock-samples into a cache
outside the repository and writes the sheet to .scratch/npc_vanilla.png by
default. The skins are Mojang's art: look at them, do not commit them.
The figures are a rough front view assembled from the 64x64 skin layout.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/"
CACHE = Path.home() / ".cache" / "asuka" / "npc"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".scratch/npc_vanilla.png")
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def fetch(rel, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE + rel) as r:
            dest.write_bytes(r.read())
    return dest


entity = json.loads(re.sub(r"//.*", "", fetch("entity/npc.entity.json", CACHE / "npc.entity.json").read_text()))
textures = entity["minecraft:client_entity"]["description"]["textures"]   # in skin-picker order

# Front view from the 64x64 skin layout: (source box, position in a 16x32 figure).
PARTS = [((8, 8, 16, 16), (4, 0)), ((20, 20, 28, 32), (4, 8)), ((44, 20, 48, 32), (0, 8)),
         ((36, 52, 40, 64), (12, 8)), ((4, 20, 8, 32), (4, 20)), ((20, 52, 24, 64), (8, 20))]
OVERLAYS = [((40, 8, 48, 16), (4, 0)), ((20, 36, 28, 48), (4, 8)), ((44, 36, 48, 48), (0, 8)),
            ((52, 52, 56, 64), (12, 8)), ((4, 36, 8, 48), (4, 20)), ((4, 52, 8, 64), (8, 20))]


def front(path):
    skin = Image.open(path).convert("RGBA")
    fig = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    for box, pos in PARTS:
        fig.paste(skin.crop(box), pos)
    for box, pos in OVERLAYS:
        fig.alpha_composite(skin.crop(box), pos)
    return fig


S, COLS = 4, 10
cw, ch = 16 * S + 28, 32 * S + 44
rows = (len(textures) + COLS - 1) // COLS
img = Image.new("RGBA", (COLS * cw + 20, rows * ch + 20), (236, 240, 244, 255))
d = ImageDraw.Draw(img)
code_font, name_font = ImageFont.truetype(FONT, 16), ImageFont.truetype(FONT, 11)
for i, (key, rel) in enumerate(textures.items()):
    x, y = 10 + (i % COLS) * cw, 10 + (i // COLS) * ch
    fig = front(fetch(rel + ".png", CACHE / f"{key}.png")).resize((16 * S, 32 * S), Image.NEAREST)
    img.alpha_composite(fig, (x + 14, y))
    d.text((x + 14, y + 32 * S + 2), f"N{i + 1:02d}", font=code_font, fill=(20, 60, 120, 255))
    d.text((x + 2, y + 32 * S + 22), key.replace("npc_", ""), font=name_font, fill=(80, 80, 80, 255))
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"wrote {OUT} ({len(textures)} skins)")
