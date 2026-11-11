# 字型轉方塊：把電腦裡的字型（書法、楷書…）畫到告示牌的格子上，每一格挑形狀最接近的方塊字，
# 做成「告示牌大字.py」裡 FONT 的寫法。用來做漢字、假名這種筆畫多、要有粗細變化的字。
#
# 告示牌一塊 4 行，每行的字高 8 單位、行距 10（上下行之間有 2 單位的縫），每格寬 8、格距 9（左右有 1 單位的縫）。
# 每一格可以放的形狀（方塊字家族）：█ ▀ ▄ ▌ ▐、四分之一方塊、下緣 1/8～7/8 的 ▁～▇、左緣 1/8～7/8 的 ▏～▉、
#   頂端 ▔、右緣 ▕，加上 --shade 時還有網點 ░▒▓（像毛筆的飛白）。
#
# 用法（在這個資料夾或 repo 根目錄都可以）：
#   python 字型轉方塊.py 春水堂 --font STXINGKA.TTF --cells 7 --png 預覽.png
#   --font  字型檔（C:\Windows\Fonts 裡的檔名或完整路徑）  --index  .ttc 裡第幾套
#   --cells 一個字最寬幾格（一塊板子最多 9 格）  --stretch 橫向拉寬倍數（預設 1.4，字比較好認）
#   --bold  筆畫加粗幾單位（0、0.5、1…）  --shade  允許用網點
# 印出來的寫法貼進 告示牌大字.py 的 FONT 就能用。
import sys, os, argparse, importlib.util
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("big", os.path.join(HERE, "告示牌大字.py"))
big = importlib.util.module_from_spec(spec); spec.loader.exec_module(big)

SS = 8   # 1 個告示牌單位畫成 8 像素

def font_path(name):
    if os.path.exists(name):
        return name
    for d in (r"C:\Windows\Fonts", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    sys.exit(f"找不到字型 {name}")

def draw_char(ch, font, index=0, cells=7, stretch=1.4, bold=0.0):
    """把一個字畫成灰階圖：寬 cells×9 單位、高 40 單位（4 行），字高佔 38 單位（第 1 行頂到第 4 行底）"""
    f = ImageFont.truetype(font_path(font), 400, index=index)
    big_img = Image.new("L", (700, 700), 0)
    ImageDraw.Draw(big_img).text((150, 100), ch, font=f, fill=255)
    bb = big_img.getbbox()
    if bb is None:
        sys.exit(f"字型 {font} 裡沒有「{ch}」")
    g = big_img.crop(bb)
    W, H = cells * 9, 40
    th = 38 * SS
    tw = min(round(g.width * th / g.height * stretch), (W - 1) * SS)
    g = g.resize((tw, th), Image.LANCZOS)
    canvas = Image.new("L", (W * SS, H * SS), 0)
    canvas.paste(g, ((W * SS - tw) // 2, 1 * SS))
    if bold > 0:
        r = max(1, round(bold * SS / 2))
        canvas = canvas.filter(ImageFilter.MaxFilter(2 * r + 1))
    return canvas

# 確定寬 9、畫在整格的字：左右兩半都有畫到的（2026-11-12 作者蓋標楷體版春水堂，截圖量出 ▏▎▐ 這類
# 只畫一半或一小條的字會被靠左畫、寬度也變窄，整行跟著歪）。半邊的字在測試牌確認之前不用。
SAFE = "█▀▄▁▂▃▅▆▇▔▙▛▜▟▚▞"

def fit(canvas, cells, shade=False, safe=True):
    """每一格（8×8 單位）挑誤差最小的方塊字，回傳 FONT 寫法"""
    cands = [(".", [[0] * 8 for _ in range(8)])] + \
            [(c, big.block_mask(c)) for c in big.BLOCKS
             if (shade or c not in "░▒▓") and (not safe or c in SAFE or (shade and c in "░▒▓"))]
    px = canvas.load()
    lines = []
    for L in range(4):
        row = ""
        for c in range(cells):
            x0, y0 = round((9 * c + 0.5) * SS), (10 * L + 1) * SS
            cov = [[sum(px[x0 + xx * SS + i, y0 + yy * SS + j] for i in range(SS) for j in range(SS)) / (255 * SS * SS)
                    for xx in range(8)] for yy in range(8)]
            best = min(cands, key=lambda cm: sum((cov[y][x] - cm[1][y][x]) ** 2 for y in range(8) for x in range(8)))
            row += best[0]
        lines.append(row)
    # 左右整欄都空的去掉（字置中用）
    while all(l[0] == "." for l in lines):
        lines = [l[1:] for l in lines]
    while all(l[-1] == "." for l in lines):
        lines = [l[:-1] for l in lines]
    return " ".join(lines)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--font", default="STXINGKA.TTF")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--cells", type=int, default=7)
    ap.add_argument("--stretch", type=float, default=1.4)
    ap.add_argument("--bold", type=float, default=0)
    ap.add_argument("--shade", action="store_true")
    ap.add_argument("--all", action="store_true", help="連半邊、細條的字也用（寬度還沒確認，蓋出來可能會歪）")
    ap.add_argument("--png")
    a = ap.parse_args()
    out = {}
    for ch in a.text:
        out[ch] = fit(draw_char(ch, a.font, a.index, a.cells, a.stretch, a.bold), a.cells, a.shade, not a.all)
        print(f'    "{ch}": "{out[ch]}",')
    if a.png:
        big.FONT.update(out)
        big.render([big.build_board([ch], "center") for ch in a.text], a.png, labels=list(a.text), white=True)
        print("預覽圖：", a.png)

if __name__ == "__main__":
    main()
