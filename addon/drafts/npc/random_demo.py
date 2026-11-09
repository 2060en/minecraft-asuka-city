"""Demo for the proposal of random faces (not decided, not in the game yet).

Run from the repository root:
    python3 addon/drafts/npc/random_demo.py

Shows what layered NPC skins could look like: the slot the author picks
gives the outfit, and the face, hairstyle, hair colour and skin tone are
combined from parts. In the game the parts would be separate textures drawn
on top of each other by extra render controllers (like the vanilla
villager's base, profession and level layers), with the choice derived from
the NPC's block position, so the same NPC always gets the same face. Here
the layers are simply composited in Python with a seeded random choice.
The demo skins go to .scratch/random_demo/, the sheet to random_demo.png.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import build as b  # noqa: E402

OUT = ROOT / ".scratch" / "random_demo"
REL = "/.scratch/random_demo"

SKIN_TONES = [(242, 208, 176), (234, 194, 158), (216, 172, 132), (190, 144, 106)]
HAIR_COLOURS = [b.HAIR_BLACK, (64, 46, 38), b.HAIR_BROWN, (128, 92, 62), b.HAIR_GREY, (206, 204, 200)]
STYLES = ["short", "cropped", "bob", "bun"]
EYES = [b.EYE, (78, 54, 36), (44, 46, 70)]


def random_face(s, rng):
    """Skin, face and hair layers; returns the skin tone for hands and legs."""
    skin = rng.choice(SKIN_TONES)
    hair = rng.choice(HAIR_COLOURS)
    b.head(s, skin=skin, hair=hair, style=rng.choice(STYLES), eyes=rng.choice(EYES), brows=rng.random() < 0.85)
    if rng.random() < 0.25:                     # glasses
        frame = (70, 72, 80)
        s.both("head", 0, 4, frame)
        s.both("head", 1, 3, frame, 2, 1)
        s.both("head", 1, 5, frame, 2, 1)
        s.paint("head", "front", 3, 4, frame, 2, 1)
    if rng.random() < 0.15:                     # beard
        beard = b.shade(hair, -1)
        s.paint("head", "front", 1, 8, beard, 6, 2, grain=3)
        s.paint("head", "front", 3, 8, b.shade(skin, -4), 2, 1)
    return skin


def staff(rng):
    s = b.Skin(rng.randrange(10 ** 6))
    random_face(s, rng)
    b.cap(s, b.NAVY, (92, 150, 210), badge=b.GOLD)
    b.shirt(s, b.WHITE_SHIRT)
    b.tie(s, (54, 92, 150))
    b.blazer(s, b.NAVY, rows=14, v=4, lining=b.shade(b.NAVY, 2), buttons=b.GOLD)
    b.sleeves(s, b.NAVY, cuff=b.WHITE_SHIRT, hands=(244, 244, 244))
    b.trousers(s, b.NAVY)
    return s


def citizen(rng):
    s = b.Skin(rng.randrange(10 ** 6))
    skin = random_face(s, rng)
    tee = rng.choice([(240, 180, 70), (110, 150, 200), (220, 220, 214), (200, 96, 90), (120, 160, 110)])
    b.shirt(s, tee)
    b.sleeves(s, tee, short=True, hands=skin, skin=skin)
    b.trousers(s, rng.choice([(70, 100, 150), (60, 60, 66), (190, 170, 130)]),
               shoe=rng.choice([(236, 236, 232), (40, 38, 40)]))
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)
    rows = [("station_staff", staff), ("citizen", citizen)]
    panels = []
    for name, make in rows:
        for i in range(8):
            make(rng).img.save(OUT / f"{name}_{i}.png")
    for name, label in (("station_staff", "站務員（同一套制服）"), ("citizen", "一般市民（同一套便服，衣服顏色也隨機）")):
        for i in range(8):
            obj = b.npc(name)
            obj["texture"] = f"{REL}/{name}_{i}.png"
            panels.append({"label": f"{label.split('（')[0]} {i + 1}",
                           "camera": {"azimuth": 20, "elevation": 8, "size": 40, "target": [0, 17, 0]},
                           "objects": [obj]})
    sheet = {"title": "提案：臉、髮型、髮色、膚色用零件隨機組合（示意，待決定）", "columns": 8,
             "panelWidth": 170, "panelHeight": 250, "background": "#e8edf1", "panels": panels}
    (HERE / "random_demo.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    subprocess.run(["node", str(ROOT / "tools/preview/render.mjs"), str(HERE / "random_demo.json"),
                    str(HERE / "random_demo.png")], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
