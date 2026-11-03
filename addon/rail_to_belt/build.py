"""Build "rail to belt": a resource pack that makes every rail look like a
conveyor belt. Textures only, no behaviour pack. Author: asuka tech.

Run from the repository root:
    python3 addon/rail_to_belt/build.py
    node tools/preview/render.mjs addon/rail_to_belt/icon_scene.json addon/rail_to_belt/icon_render.png
    python3 addon/rail_to_belt/build.py --icon

The first run draws the rail textures into pack/textures/blocks/ and writes
the icon scene; the render draws a short piece of belt; --icon crops it into
pack/pack_icon.png. Everything here is drawn by this script, so the whole
pack is committed; addon/build/rail to belt.mcpack is the installable file.

The look comes from the conveyor draft the author approved
(addon/drafts/conveyor/, 2026-11-01): a black rubber belt with ribs across
it and steel side rails. Seen from above, as a rail is, the side rails are
thin strips at the edges. The kind of rail shows as a coloured line inside
each side rail (the yellow line was the approved mark of the powered
conveyor; it gets brighter while the rail is on). Only plain rails curve, so
only the plain rail has a curved texture.

Vanilla layout (bedrock-samples): straight rails run top to bottom; the
curved rail joins the bottom and right edges, its outer rail toward the top
left.
"""
import argparse
import json
import math
import shutil
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACK = HERE / "pack"
REL = "/addon/rail_to_belt"

# colours of the approved conveyor draft
BELT = (46, 48, 51, 255)
BELT_RIB = (60, 63, 67, 255)
BELT_EDGE = (34, 35, 37, 255)
RAIL_TOP = (211, 215, 219, 255)
RAIL_SHADE = (143, 149, 155, 255)

# The line inside the side rails: (off, on). Plain rails have none.
MARKS = {
    "golden": ((227, 181, 40, 255), (255, 226, 92, 255)),    # powered rail: the approved yellow
    "detector": ((176, 44, 38, 255), (255, 84, 72, 255)),    # red (Claude's pick)
    "activator": ((52, 112, 196, 255), (110, 176, 255, 255)),  # blue (Claude's pick)
}


def straight(mark=None):
    """A belt running top to bottom: side rail, line, belt with ribs."""
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            if x in (0, 15):
                c = RAIL_SHADE
            elif x in (1, 14):
                c = RAIL_TOP
            elif x in (2, 13):
                c = mark or BELT_EDGE
            else:
                c = BELT_RIB if y % 2 == 0 else BELT
            px[x, y] = c
    return img


def curve():
    """A belt joining the bottom and right edges: the outer side rail runs
    along the top and left edges, the inner one is a small quarter circle
    round the bottom-right corner, ribs radiate from that corner."""
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            d = math.hypot(15.5 - x, 15.5 - y)
            edge = min(x, y)
            if edge == 0:
                c = RAIL_SHADE
            elif edge == 1:
                c = RAIL_TOP
            elif d < 1:                      # the inner rail lines up with a
                c = RAIL_SHADE               # straight's: shade, top, edge
            elif d < 2:
                c = RAIL_TOP
            elif edge == 2 or d < 3:
                c = BELT_EDGE
            else:
                c = BELT
            px[x, y] = c
    # ribs every 12 degrees from the inner corner, as in the draft's curve
    for k in range(8):
        theta = math.radians(6 + 12 * k)
        r = 4.0
        while r < 23:
            x = int(16 - r * math.cos(theta))
            y = int(16 - r * math.sin(theta))
            if 3 <= x < 16 and 3 <= y < 16 and px[x, y] == BELT:
                px[x, y] = BELT_RIB
            r += 0.25
    return img


def textures():
    out = {"rail_normal": straight(), "rail_normal_turned": curve()}
    for kind, (off, on) in MARKS.items():
        out[f"rail_{kind}"] = straight(off)
        out[f"rail_{kind}_powered"] = straight(on)
    return out


MANIFEST = {
    "format_version": 2,
    "header": {
        "name": "rail to belt",
        "description": "把鐵軌換成履帶的樣子（只換材質）",
        "uuid": "6f1d4a3e-2b7c-4e8a-9c51-3d2f8b7a6e10",
        "version": [1, 0, 0],
        "min_engine_version": [1, 21, 0],
    },
    "modules": [{"type": "resources", "uuid": "b2e8c7d4-5a91-4f36-8e0b-7c4d1a9f2e35", "version": [1, 0, 0]}],
    "metadata": {"authors": ["asuka tech"]},
}


def write_pack():
    tex_dir = PACK / "textures" / "blocks"
    tex_dir.mkdir(parents=True, exist_ok=True)
    tex = textures()
    for name, img in tex.items():
        img.save(tex_dir / f"{name}.png")
    (PACK / "manifest.json").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tex


def icon_scene(tex):
    """A short piece of belt on a light floor: powered straight, plain
    straight, the curve, plain straight, powered straight."""
    names = ["rail_normal", "rail_normal_turned", "rail_golden_powered"]
    tiles = [tex[n] for n in names] + [tex["rail_normal"].rotate(90), tex["rail_golden_powered"].rotate(90)]
    atlas = Image.new("RGBA", (16 * len(tiles), 16))
    for i, t in enumerate(tiles):
        atlas.paste(t, (16 * i, 0))
    atlas.save(HERE / "icon_atlas.png")
    geos = []
    for i in range(len(tiles)):
        face = {"uv": [16 * i, 0], "uv_size": [16, 16]}
        geos.append({"description": {"identifier": f"geometry.tile_{i}", "texture_width": atlas.width, "texture_height": 16},
                     "bones": [{"name": "tile", "pivot": [0, 0, 0], "cubes": [
                         {"origin": [-8, 16, -8], "size": [16, 0.4, 16], "uv": {"up": face}}]}]})
    (HERE / "icon_scene.geo.json").write_text(json.dumps({"format_version": "1.12.0", "minecraft:geometry": geos}, indent=1) + "\n",
                                              encoding="utf-8")
    floor = {"up": "#d9dcdf", "south": "#b9bdc1", "north": "#b9bdc1", "east": "#a7abaf", "west": "#a7abaf", "down": "#8d9195"}
    objs = []
    for gx in (-16, 0, 16):
        for gz in (-16, 0, 16):
            objs.append({"type": "block", "color": floor, "origin": [gx - 8, 0, gz - 8], "size": [16, 16, 16]})

    def tile(i, gx, gz):
        return {"type": "geo", "geo": f"{REL}/icon_scene.geo.json", "identifier": f"geometry.tile_{i}",
                "texture": f"{REL}/icon_atlas.png", "position": [gx, 0, gz]}
    objs += [tile(2, -16, 16), tile(0, -16, 0), tile(1, -16, -16), tile(3, 0, -16), tile(4, 16, -16)]
    sheet = {"columns": 1, "panelWidth": 640, "panelHeight": 640, "background": "#ffffff",
             "panels": [{"label": "", "camera": {"azimuth": 225, "elevation": 35, "size": 78, "target": [0, 6, 0]},
                         "objects": objs}]}
    (HERE / "icon_scene.json").write_text(json.dumps(sheet, indent=1) + "\n", encoding="utf-8")


def make_icon():
    render = Image.open(HERE / "icon_render.png").convert("RGB")
    render = render.crop((0, 0, render.width, render.height - 36))     # drop the label strip
    bg = Image.new("RGB", render.size, (255, 255, 255))
    from PIL import ImageChops
    l, t, r, b = ImageChops.difference(render, bg).getbbox()           # the drawing itself
    side = max(r - l, b - t) * 1.08                                     # an even margin round it
    cx, cy = (l + r) / 2, (t + b) / 2
    box = (round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2))
    square = Image.new("RGB", (box[2] - box[0], box[3] - box[1]), (255, 255, 255))
    square.paste(render.crop(box), (0, 0))
    square.resize((512, 512), Image.LANCZOS).save(PACK / "pack_icon.png")


def mcpack():
    out = ROOT / "addon" / "build" / "rail to belt.mcpack"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PACK.rglob("*")):
            if f.is_file():
                z.write(f, Path("rail to belt") / f.relative_to(PACK))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--icon", action="store_true", help="crop icon_render.png into pack/pack_icon.png")
    args = parser.parse_args()
    if args.icon:
        make_icon()
    else:
        icon_scene(write_pack())
    mcpack()
