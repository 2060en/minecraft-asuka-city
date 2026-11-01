"""Draw a contact sheet of the 60 vanilla NPC skins, numbered N01-N60.

Run from the repository root:
    python3 addon/drafts/npc/vanilla_sheet.py [out.png]

Downloads the skins from Mojang's official bedrock-samples into a cache
outside the repository and writes the sheet to .scratch/npc_vanilla.png by
default. The skins are Mojang's art: look at them, do not commit them.
The figures are a rough front view assembled from the NPC's own skin layout
(geometry.npc, a villager-shaped model with a 10-pixel head, a nose, a robe
layer and folded arms; see build.py), not the player skin layout.
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

# Front view from the NPC layout: (source box, position in a 16x34 figure).
# Body and legs first, then the robe over them, the arms, the head and the nose.
PARTS = [((22, 26, 30, 38), (4, 10)), ((4, 26, 8, 38), (4, 22)), ((4, 26, 8, 38), (8, 22)),
         ((6, 44, 14, 62), (4, 10)), ((48, 26, 52, 34), (0, 10)), ((48, 50, 52, 58), (12, 10)),
         ((44, 42, 52, 46), (4, 15)), ((8, 8, 16, 18), (4, 0)), ((26, 2, 28, 6), (7, 7))]


def front(path):
    skin = Image.open(path).convert("RGBA")
    fig = Image.new("RGBA", (16, 34), (0, 0, 0, 0))
    for box, pos in PARTS:
        fig.alpha_composite(skin.crop(box), pos)
    return fig


S, COLS = 4, 10
cw, ch = 16 * S + 28, 34 * S + 44
rows = (len(textures) + COLS - 1) // COLS
img = Image.new("RGBA", (COLS * cw + 20, rows * ch + 20), (236, 240, 244, 255))
d = ImageDraw.Draw(img)
code_font, name_font = ImageFont.truetype(FONT, 16), ImageFont.truetype(FONT, 11)
for i, (key, rel) in enumerate(textures.items()):
    x, y = 10 + (i % COLS) * cw, 10 + (i // COLS) * ch
    fig = front(fetch(rel + ".png", CACHE / f"{key}.png")).resize((16 * S, 34 * S), Image.NEAREST)
    img.alpha_composite(fig, (x + 14, y))
    d.text((x + 14, y + 34 * S + 2), f"N{i + 1:02d}", font=code_font, fill=(20, 60, 120, 255))
    d.text((x + 2, y + 34 * S + 22), key.replace("npc_", ""), font=name_font, fill=(80, 80, 80, 255))
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(f"wrote {OUT} ({len(textures)} skins)")
