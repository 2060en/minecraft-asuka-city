"""各樓層的平面圖：用模型網頁的正投影（正上方、北方在上）截圖，再加上標題、參考點編號與告示牌文字。

用法（先跑過 extract.py 與 build.py）：

    tools/world-model/.venv/Scripts/python.exe tools/world-model/plans.py <資料夾> <網頁.html> --preset akq --out <平面圖資料夾>

樓層由範圍設定的 floors 決定：floor 是地板高度，lo～hi 是要顯示的高度。
告示牌在同一層不超過 40 個才標出來，太多會蓋住平面。需要 node（截圖用 shot.mjs）。
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/msjh.ttc"              # 微軟正黑體
PX = 8                                          # 每格幾像素
MARGIN = (16, 10, 4, 4)                         # 左、上、右、下留幾格（放座標尺的字）
HEAD = 110                                      # 標題列的高度
SIGN_LIMIT = 40


def load_preset(name):
    path = Path(name) if name.endswith(".json") else HERE / "presets" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sign_texts(block_entities):
    out = []
    for e in block_entities:
        if e.get("id") in ("Sign", "HangingSign"):
            sides = [((e.get(k) or {}).get("Text") or "").replace("\n", " ").strip() for k in ("FrontText", "BackText")]
            text = " / ".join(t for t in sides if t)
            if text:
                out.append((e["x"], e["y"], e["z"], text))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="各樓層的平面圖")
    parser.add_argument("data", help="extract.py 的輸出資料夾")
    parser.add_argument("html", help="build.py 做出的網頁")
    parser.add_argument("--preset", required=True)
    parser.add_argument("--out", required=True, help="平面圖的輸出資料夾")
    args = parser.parse_args()

    preset = load_preset(args.preset)
    meta = json.loads((Path(args.data) / "meta.json").read_text(encoding="utf-8"))
    signs = sign_texts(json.loads((Path(args.data) / "block_entities.json").read_text(encoding="utf-8")))
    (ox, oy, oz), (sx, sy, sz) = meta["origin"], meta["size"]
    left, top = ox - MARGIN[0], oz - MARGIN[1]
    right, bottom = ox + sx + MARGIN[2], oz + sz + MARGIN[3]
    width, height = (right - left) * PX, (bottom - top) * PX
    floors = preset.get("floors") or [{"name": "全部", "floor": oy, "lo": oy, "hi": oy + sy - 1, "note": ""}]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="asuka_plans_") as tmp:
        views = [{"name": f"plan_{i}", "hi": f["hi"], "lo": f["lo"], "top": [(left + right) / 2, (top + bottom) / 2, PX],
                  "size": [width, height], "panel": False} for i, f in enumerate(floors)]
        (Path(tmp) / "views.json").write_text(json.dumps(views), encoding="utf-8")
        subprocess.run(["node", str(HERE / "shot.mjs"), args.html, tmp, str(Path(tmp) / "views.json")], check=True)

        f_title, f_sub, f_pt, f_sign = (ImageFont.truetype(FONT, s) for s in (34, 20, 22, 15))
        points = preset.get("points", [])
        for i, f in enumerate(floors):
            img = Image.open(Path(tmp) / f"plan_{i}.png").convert("RGB")
            canvas = Image.new("RGB", (img.width, img.height + HEAD), "white")
            canvas.paste(img, (0, HEAD))
            d = ImageDraw.Draw(canvas)

            def at(x, z):
                return (x - left) * PX, (z - top) * PX + HEAD

            d.text((20, 12), f"{preset['title']}　{f['name']}（地板 Y{f['floor']}，顯示 Y{f['lo']}～{f['hi']}）", font=f_title, fill="#123")
            d.text((20, 58), f.get("note", ""), font=f_sub, fill="#444")
            legend = f"資料：世界 {meta.get('world', '')}（{meta.get('saved', '')} 的存檔）　北方在上，每條格線 10 格"
            if points:
                legend += f"　紅圈數字＝{preset.get('points_title', '參考點')}"
            d.text((20, 82), legend, font=f_sub, fill="#666")

            here = [s for s in signs if f["lo"] <= s[1] <= f["hi"]]
            if len(here) <= SIGN_LIMIT:
                placed = []
                for x, y, z, text in sorted(here, key=lambda s: (s[2], s[0])):
                    u, v = at(x + 0.5, z + 0.5)
                    d.rectangle((u - 3, v - 3, u + 3, v + 3), fill="#d33")
                    w = d.textlength(text[:28], font=f_sign)
                    box = [u + 6, v - 10, u + 10 + w, v + 10]
                    # 和已經放好的標籤重疊時往下挪
                    while any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in placed):
                        box[1] += 22
                        box[3] += 22
                    if box[1] != v - 10:
                        d.line((u, v, box[0], box[1] + 10), fill="#d33", width=1)
                    placed.append(box)
                    d.rectangle(box, fill=(255, 255, 220), outline="#999")
                    d.text((box[0] + 2, box[1] + 1), text[:28], font=f_sign, fill="#000")

            # 參考點：站立高度（腳下那一格）落在這一層的範圍內才畫
            for n, p in enumerate(points, 1):
                x, y, z = p["p"]
                nxt = floors[i + 1]["floor"] if i + 1 < len(floors) else f["hi"] + 3
                if f["floor"] <= y < nxt:
                    u, v = at(x + 0.5, z + 0.5)
                    d.ellipse((u - 15, v - 15, u + 15, v + 15), fill="#e8263b", outline="white", width=2)
                    label = str(n)
                    d.text((u - d.textlength(label, font=f_pt) / 2, v - 14), label, font=f_pt, fill="white")

            name = out / f"平面圖_{i + 1}_{f['name']}_Y{f['floor']}.png"
            canvas.save(name, optimize=True)
            print(f"平面圖：{name.name}（這一層的告示牌 {len(here)} 個{'，太多不標' if len(here) > SIGN_LIMIT else ''}）")


if __name__ == "__main__":
    main()
