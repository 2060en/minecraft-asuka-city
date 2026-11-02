"""Build the NPC slot picker: a page that shows each of the 60 vanilla NPC
skins next to fields for the author to fill in (replace or keep, with whom,
what they look like) and the drafts that exist so far.

Run from the repository root, after build.py:
    python3 addon/drafts/npc/picker.py

Writes everything to .scratch/npc_picker/ (index.html plus img/), which is
not committed: the slot images are renders of Mojang's vanilla skins. The
skins are downloaded into the same cache as vanilla_sheet.py uses. The page
is published as a private claude.ai artifact; it saves what the author
types in the artifact's database (collection "slots", one document per slot,
id N01 ... N60), where Claude reads it back.
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / ".scratch" / "npc_picker"
TEX = OUT / "tex"
IMG = OUT / "img"
BASE = "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/"
CACHE = Path.home() / ".cache" / "asuka" / "npc"
BACKDROP = "#dfe5ea"
PW, PH, LABEL = 150, 210, 36

sys.path.insert(0, str(HERE))
from build import CHARACTERS  # noqa: E402  (the drafts' ids and names)

# Vanilla categories in skin-picker order, with what the vanilla skins look
# like and Claude's candidates (proposals, see docs/npc.md).
CATEGORIES = [
    ("general", "一般人物", 10, "穿便服的一般人。N01～N05 是長髮、穿洋裝或裙子的女性，N06～N10 是穿便服的男性。",
     ["觀光客（背包客）", "滑雪客", "海灘遊客", "拉行李箱的旅客", "通勤的上班族", "高中生（制服）", "老人",
      "咖啡店店員", "便利商店店員", "飯店櫃台人員"]),
    ("scientist", "科學家", 10, "N11～N18 穿白色實驗衣；N19 是黃色防護衣加防毒面具，N20 是灰色的方頭機器人。",
     ["醫師", "護理師", "藥劑師", "Asuka Inc. 研發中心的研究員", "氣象局的預報員", "海生館的研究員",
      "晶圓廠無塵衣", "Asuka Inc. 的機器人"]),
    ("apiary", "養蜂人", 5, "N21 穿養蜂防護衣、戴面紗，N22、N23 穿工作服，N24 穿蜜蜂花紋的圍裙，N25 是蜜蜂頭的吉祥物。",
     ["消防員", "救護員", "潛水員", "吉祥物"]),
    ("teacher", "老師", 5, "穿便服的大人，N27 手上拿著一本書。",
     ["老師", "大學教授", "高中生（另一款）", "圖書館員", "美術館的導覽員"]),
    ("construction", "建築工人", 5, "戴安全帽、穿反光背心。",
     ["工地工人", "工地主任", "機場地勤（指揮飛機）", "鐵路維修員", "清潔人員"]),
    ("agriculture", "農業", 10, "農夫、園丁，工作服居多；N39 是稻草人。",
     ["農民", "牧場", "漁民", "魚市場攤販", "皇居離宮的庭師", "蔬果攤販", "造船廠工人", "稻草人"]),
    ("mobs", "生物造型的商人", 5, "穿西裝、襯衫的動物頭角色（例如貓、熊貓、狐狸），不是人類。",
     ["Minecraft Studio 的玩偶裝"]),
    ("business", "上班族", 5, "穿襯衫、西裝的上班族；N52 不是人，是辦公室的飲水機。",
     ["站務員", "機師", "空服員", "警察", "黒潮特快的移民官", "自動販賣機"]),
    ("kiosk", "服務台", 5, "不是人形，是帶螢幕的服務機台；N58 是飄在空中的小螢幕。",
     ["機場的自助報到機", "車站的旅客服務機", "數位導覽看板", "Asuka Inc. 總部的接待機", "展覽中心的導覽機"]),
]


def fetch(rel, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(BASE + rel) as r:
            dest.write_bytes(r.read())
    return dest


def slots():
    entity = json.loads(re.sub(r"//.*", "", fetch("entity/npc.entity.json", CACHE / "npc.entity.json").read_text()))
    textures = entity["minecraft:client_entity"]["description"]["textures"]
    cats = [c for c in CATEGORIES for _ in range(c[2])]
    assert len(cats) == len(textures) == 60
    out = []
    for i, ((key, rel), cat) in enumerate(zip(textures.items(), cats)):
        code = f"N{i + 1:02d}"
        shutil.copy(fetch(rel + ".png", CACHE / f"{key}.png"), TEX / f"{code}.png")
        out.append({"code": code, "file": f"{key}.png", "cat": cat[0]})
    return out


def render(items):
    """Render front and back of each (name, texture) and save one image per item."""
    rel = "/" + str(OUT.relative_to(ROOT))
    panels = []
    for name, tex in items:
        for az in (25, 205):
            panels.append({"camera": {"azimuth": az, "elevation": 10, "size": 38, "target": [0, 17, 0]},
                           "objects": [{"type": "geo", "geo": "/addon/drafts/npc/npc_preview.geo.json",
                                        "texture": tex if tex.startswith("/addon") else f"{rel}/tex/{tex}",
                                        "rotationY": 180}]})
    cols = 20
    sheet = {"columns": cols, "panelWidth": PW, "panelHeight": PH, "background": BACKDROP, "panels": panels}
    (OUT / "sheet.json").write_text(json.dumps(sheet))
    subprocess.run(["node", str(ROOT / "tools/preview/render.mjs"), str(OUT / "sheet.json"), str(OUT / "sheet.png")],
                   check=True, cwd=ROOT)
    big = Image.open(OUT / "sheet.png").convert("RGB")
    for k, (name, _) in enumerate(items):
        pair = Image.new("RGB", (2 * PW, PH))
        for j in range(2):
            i = 2 * k + j
            x, y = (i % cols) * PW, (i // cols) * (PH + LABEL)
            pair.paste(big.crop((x, y, x + PW, y + PH)), (j * PW, 0))
        pair.save(IMG / f"{name}.png", optimize=True)


def main():
    for d in (TEX, IMG):
        d.mkdir(parents=True, exist_ok=True)
    slot_list = slots()
    drafts = [{"id": k, "name": v[0]} for k, v in CHARACTERS.items()]
    render([(s["code"], f"{s['code']}.png") for s in slot_list] +
           [(f"d_{d['id']}", f"/addon/drafts/npc/skins/{d['id']}.png") for d in drafts])
    data = {
        "categories": [{"id": c[0], "name": c[1], "vanilla": c[3], "candidates": c[4]} for c in CATEGORIES],
        "slots": slot_list,
        "drafts": drafts,
    }
    page = (HERE / "picker.html").read_text(encoding="utf-8")
    page = page.replace("/*PICKER_DATA*/null", json.dumps(data, ensure_ascii=False))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}/index.html and {len(list(IMG.glob('*.png')))} images")


if __name__ == "__main__":
    main()
