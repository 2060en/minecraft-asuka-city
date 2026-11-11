# 告示牌大字產生器（基岩版）
#
# 字形來源：Reddit r/Minecraft「Some new sign letters (tutorial in comments)」，大寫原作 Hugleton、
#   小寫 sreave15、數字與符號 DaisyEseyad；網頁產生器 https://main.daisyeseyad.workers.dev/bigsigntext
# 原作是 Java 版，靠 Java 每個符號寬度不同（▊ ▏ ◢ …）拼出形狀。基岩版只要一行混了方塊字，整行就變成
#   等寬字型：方塊字一個 9、半形空白一個 4，◢◣◤◥ 又只是很小的三角形，所以照抄會歪。
#   這裡保留原作每個字母的樣子（3 格寬、4 行高、切角、中間半格橫槓），改用四分之一方塊（▘▝▖▗▙▛▜▟…）重拼。
#
# 用法：
#   python 告示牌大字.py "Yoshinoya"                     印出板子數和每塊的複製區
#   python 告示牌大字.py "Yoshinoya" --png 預覽.png       另外畫一張排在牆上的預覽圖
#   python 告示牌大字.py "Yoshinoya" --upper              全部轉大寫
#   python 告示牌大字.py "FamilyMart" --center            整排置中（預設靠左）；--boards 5 指定用幾塊
#   python 告示牌大字.py --sheet 字母表.png                畫出整套字母表
#   加 --white 預覽成白字（深色木頭用）
import sys, argparse
from itertools import product

BOARD_W = 96        # 一塊告示牌的寬度（告示牌單位；一行最多 89 時左右各留 3.5）
LIMIT = 89          # 一行最多 89，超過會在空白處自動換行
FULL, HALF = 9, 4   # 等寬字型：方塊字一個 9、半形空白一個 4
# 一格空白只能用半形空白湊：基岩版沒有「看不見又寬 9」的字（2026-11-11 作者蓋測試牌：全形空白會畫出虛線框，
#   點字空白和字型圖裡空白的字都只有 4 寬）。所以連續的空格加字距整段算，打最接近的半形空白數，
#   再整塊 4 行一起窮舉行頭行尾空白，讓同一欄方塊上下落差最小（理論上最少還會差 1～1.5，約六分之一格）。

# 四分之一方塊：（左上, 右上, 左下, 右下）；"." 代表一整格空白
QUAD = {"█": (1, 1, 1, 1), "▀": (1, 1, 0, 0), "▄": (0, 0, 1, 1), "▌": (1, 0, 1, 0), "▐": (0, 1, 0, 1),
        "▘": (1, 0, 0, 0), "▝": (0, 1, 0, 0), "▖": (0, 0, 1, 0), "▗": (0, 0, 0, 1),
        "▚": (1, 0, 0, 1), "▞": (0, 1, 1, 0), "▛": (1, 1, 1, 0), "▜": (1, 1, 0, 1),
        "▙": (1, 0, 1, 1), "▟": (0, 1, 1, 1), ".": (0, 0, 0, 0)}

# 字母表：4 行用空白隔開，每個字元是一格（"." 是空格）。每個字母 4 行的格數要一樣。
# 新增字母時照這個格式加一行，跑 --sheet 看樣子。
FONT = {
    # 大寫（Hugleton）
    "A": "▟█▙ █.█ ███ █.█",
    "B": "██▙ █▄▛ █▀▙ ██▛",
    "C": "▟█▙ █.▀ █.▄ ▜█▛",
    "D": "██▙ █.█ █.█ ██▛",
    "E": "███ █▄▄ █▀▀ ███",
    "F": "███ █▄▄ █▀▀ █..",
    "G": "▟█▙ █.▀ █▝█ ▜██",
    "H": "█.█ █▄█ █▀█ █.█",
    "I": "███ .█. .█. ███",
    "J": "..█ ..█ ▄.█ ▜█▛",
    "K": "█▗▛ █▛. █▙. █▝▙",
    "L": "█.. █.. █.. ███",
    # M、W 原作也是 3 格寬（中間那格用細斜線拼 V）；四分之一方塊在 3 格裡拼不出斜 V，改成頂端中間凹一格。
    # 4 格寬的 "█▖▗█ █▜▛█ █..█ █..█" 比較像，但會讓一塊板子塞不下 3 個字、字距變亂，所以不用。
    "M": "▛▄▜ █▀█ █.█ █.█",
    "N": "█▖█ █▙█ █▜█ █▝█",
    "O": "▟█▙ █.█ █.█ ▜█▛",
    "P": "██▙ █.█ ██▛ █..",
    "Q": "▟█▙ █.█ █▚█ ▜█▛",
    "R": "██▙ █.█ ██▛ █▝▙",
    "S": "▟█▙ █▄▀ ▄▀█ ▜█▛",
    "T": "███ .█. .█. .█.",
    "U": "█.█ █.█ █.█ ▜█▛",
    "V": "█.█ █.█ ▜.▛ ▝█▘",
    "W": "█.█ █.█ █▄█ ▙▀▟",
    "X": "▜.▛ ▝█▘ ▗█▖ ▟.▙",
    "Y": "▜.▛ ▝█▘ .█. .█.",
    "Z": "███ .▟▛ ▟▛. ███",
    # 小寫（sreave15）：第 1 行留給 b d f h i j k l t 往上伸的部分
    "a": "... ▀▀▄ ▟▀█ ▜▄█",
    "b": "█.. █▀▙ █.█ █▄▛",
    "c": "... ▟▀▙ █.. ▜▄▛",
    "d": "..█ ▟▀█ █.█ ▜▄█",
    "e": "... ▟▀▙ █▀▀ ▜▄▛",
    "f": ".▟▀ .█. ▀█▀ .█.",
    "g": "... ▟▀█ ▜▄█ ▄▄▛",
    "h": "█.. █▀▙ █.█ █.█",
    "i": ".▀. .█. .█. .█.",
    "j": "..▀ ..█ ..█ ▜▄▛",
    "k": "█.. █▗▛ ██. █▝▙",
    "l": ".█. .█. .█. .█.",
    "m": "... ▛█▜ ▌█▐ ▌█▐",
    "n": "... █▀▙ █.█ █.█",
    "o": "... ▟▀▙ █.█ ▜▄▛",
    "p": "... █▀▙ █▄▛ █..",
    "q": "... ▟▀█ ▜▄█ ..█",
    "r": "... █▀▙ █.▀ █..",
    "s": "... ▟▀▀ ▀▀▙ ▄▄▛",
    "t": ".█. ▀█▀ .█. .█.",
    "u": "... █.█ █.█ ▜▄█",
    "v": "... █.█ ▜.▛ ▝█▘",
    "w": "... ▌█▐ ▌█▐ ▙█▟",
    "x": "... ▜.▛ .█. ▟.▙",
    "y": "... █.█ ▜▄█ ▄▄▛",
    "z": "... ▀▜▛ ▗▛. █▄▄",
    # 數字（DaisyEseyad）
    "0": "▟█▙ █▖█ █▝█ ▜█▛",
    "1": "▟█. .█. .█. ███",
    "2": "▟█▙ ▀▟▛ ▟▛. ███",
    "3": "▟█▙ ▀▄▛ ▄▀▙ ▜█▛",
    "4": "█.█ █.█ ███ ..█",
    "5": "███ █▄▄ ▄.█ ▜█▛",
    "6": "▟██ █▄▄ █.█ ▜█▛",
    "7": "███ .▗█ .█▘ .█.",
    "8": "▟█▙ ▜▄▛ ▟▀▙ ▜█▛",
    "9": "▟█▙ █.█ ▜▄█ ▄▄▛",
    # 符號
    " ": ". . . .",
    ".": ". . . █",
    ",": ". . ▄ ▛",
    "!": "█ █ ▀ █",
    "?": "▟█▙ .▄▛ .▀. .█.",
    "-": ".. ▄▄ ▀▀ ..",
    ":": ". █ . █",
    "'": "█ ▀ . .",
}

def glyph(ch):
    rows = FONT[ch].split(" ")
    assert len(rows) == 4 and len({len(r) for r in rows}) == 1, f"字母 {ch!r} 的 4 行格數不一樣"
    for r in rows:
        for c in r:
            assert c in QUAD, f"字母 {ch!r} 用了沒驗證過的字 {c!r}"
    return rows

def ideal_w(chs):
    """一塊板子上這些字母的理想寬度（每格都算 9）"""
    return sum(len(glyph(c)[0]) * FULL for c in chs) + HALF * (len(chs) - 1)

def pack(text, cap1=LIMIT):
    """一個字母都不切開，盡量塞滿每塊板子（一行不超過 89）。板子頭尾的空白字元拿掉，記下單字在哪裡換板子。
    cap1：第 1 塊最多放多寬（置中時用來調整第 1 塊放幾個字）。"""
    boards, cur, breaks = [], [], set()

    def close():
        nonlocal cur
        cut = bool(cur) and cur[-1] == " "
        while cur and cur[-1] == " ":
            cur.pop()
        if cur:
            boards.append(cur)
        if cut:
            breaks.add(len(boards))
        cur = []

    for ch in text:
        if ch == " " and not cur:          # 板子開頭的空白：不寫，記成換板子處的單字間隔
            if boards:
                breaks.add(len(boards))
            continue
        if cur and ideal_w(cur + [ch]) > (cap1 if not boards else LIMIT):
            close()
            if ch == " ":
                breaks.add(len(boards))
                continue
        cur.append(ch)
    close()
    return boards, sorted(x for x in breaks if 0 < x < len(boards))

def row_seq(chs, r):
    """第 r 行拆成「空白段、方塊、空白段、方塊…空白段」：
    [("run", 理想寬), ("blk", 字, 理想位置), ...]。連續的空格（每格理想寬 9）和字距（4）合併成一段。"""
    seq, xi, run = [], 0, 0
    for j, ch in enumerate(chs):
        if j:
            run += HALF; xi += HALF
        for c in glyph(ch)[r]:
            if c == ".":
                run += FULL
            else:
                seq.append(("run", run)); run = 0
                seq.append(("blk", c, xi))
            xi += FULL
    seq.append(("run", run))
    return seq

def build_board(chs, align):
    """回傳 4 行字串。align：'center' 置中、'left' 靠左、'right' 靠右。
    多塊板子時，最後一塊靠左、（置中排法的）第 1 塊靠右，板子交界的字距才接得上。"""
    W = ideal_w(chs)
    frame = (BOARD_W - LIMIT) / 2
    x_ideal = {"left": frame, "right": frame + LIMIT - W, "center": (BOARD_W - W) / 2}[align]
    seqs = [row_seq(chs, r) for r in range(4)]
    rows = [row_cands(seq, x_ideal) for seq in seqs]
    # 4 行一起窮舉：先求同一欄方塊在 4 行之間落差最小，再求整塊離理想位置最近、空白最少
    best = None
    for pick in product(*rows):
        pos = {}
        dev = 0
        for (xs, _, _), seq in zip(pick, seqs):
            for q, x in zip([q for q in seq if q[0] == "blk"], xs):
                pos.setdefault(q[2], []).append(x)
                dev = max(dev, abs(x - (x_ideal + q[2])))
        spread = max((max(v) - min(v) for v in pos.values()), default=0)
        key = (spread, dev, sum(p[2] for p in pick))
        if best is None or key < best[0]:
            best = (key, [p[1] for p in pick])
    return best[1]

def row_cands(seq, target, slack=4):
    """一行所有可行的打法：[(各方塊位置, 字串, 空白數)]，只留離理想位置 slack 以內的"""
    runs = [s[1] for s in seq if s[0] == "run"]
    F = sum(1 for s in seq if s[0] == "blk")
    if F == 0:
        return [((), " " * max(1, round(runs[0] / HALF)), 0)]
    opts = [[w // HALF] if w % HALF == 0 else [w // HALF, w // HALF + 1] for w in runs]
    out = {}
    for combo in product(*opts):
        N = sum(combo)
        room = (LIMIT - FULL * F - HALF * N) // HALF
        if room < 0:
            continue
        base, x, i = [], (BOARD_W - FULL * F - HALF * N) / 2, 0
        body = ""
        for s in seq:
            if s[0] == "run":
                x += HALF * combo[i]; body += " " * combo[i]; i += 1
            else:
                base.append((x, s[2])); body += s[1]; x += FULL
        for d in range(-room, room + 1):
            xs = tuple(v + 2 * d for v, _ in base)
            if max(abs(v - (target + c)) for v, (_, c) in zip(xs, base)) > slack:
                continue
            a, b = max(d, 0), max(-d, 0)
            cand = (xs, " " * a + body + " " * b, N + a + b)
            if xs not in out or cand[2] < out[xs][2]:
                out[xs] = cand
    if not out:   # 理論上不會發生；放寬限制再試
        return row_cands(seq, target, slack + 4)
    return list(out.values())

def board_spread(chs, lines):
    """檢查用：同一欄方塊在 4 行之間實際位置的最大落差（照遊戲的寬度規則從字串算回去）"""
    pos = {}
    for r, ln in enumerate(lines):
        cols = [q[2] for q in row_seq(chs, r) if q[0] == "blk"]
        x = (BOARD_W - width(ln)) / 2
        k = 0
        for c in ln:
            if c == " ":
                x += HALF
            else:
                pos.setdefault(cols[k], []).append(x); k += 1; x += FULL
    return max((max(v) - min(v) for v in pos.values()), default=0)

def width(line):
    return sum(HALF if c == " " else FULL for c in line)

def layout(text, center=False, n_boards=None):
    """回傳（板子, 換單字處, 每塊的 4 行, 偏移）。
    靠左（預設）：盡量塞滿，最後一塊靠左，空的都在右邊。
    置中：第 1 塊靠右、最後一塊靠左、中間照常；試各種「第 1 塊放幾個字」，挑左右空白最接近的。
      偏移＝整排字往右偏多少（告示牌單位，31 約一個字）；n_boards 可以指定用幾塊（多一塊常常就能正中間）。"""
    if not center:
        boards, breaks = pack(text)
        n = len(boards)
        aligns = ["left"] if n == 1 else ["center"] * (n - 1) + ["left"]
        return boards, breaks, [build_board(b, a) for b, a in zip(boards, aligns)], 0
    best = None
    for cap1 in range(1, LIMIT + 1):
        boards, breaks = pack(text, cap1)
        n = len(boards)
        if n_boards and n != n_boards:
            continue
        off = 0 if n == 1 else ((LIMIT - ideal_w(boards[0])) - (LIMIT - ideal_w(boards[-1]))) / 2
        key = (n, abs(off))
        if best is None or key < best[0]:
            best = (key, boards, breaks, off)
    if best is None:
        sys.exit(f"排不成 {n_boards} 塊板子")
    _, boards, breaks, off = best
    n = len(boards)
    aligns = ["center"] if n == 1 else ["right"] + ["center"] * (n - 2) + ["left"]
    return boards, breaks, [build_board(b, a) for b, a in zip(boards, aligns)], off

# ---------- 預覽圖：每個方塊字畫成 8×8 的格子（四分之一方塊各 4×4），前進 9 ----------
# 遊戲字型圖裡這些字剛好就是整齊的四分之一格，所以直接畫就跟遊戲一樣，不需要附上遊戲的字型圖。
def render(all_lines, dst, labels=None, white=False, per_row=None):
    from PIL import Image, ImageDraw, ImageFont
    S = 6                      # 1 個告示牌單位畫成 6 像素
    BH, PITCH, TOP = 48, 10, 4 # 板子高 48、行距 10、字高 8（2026-11-11 用遊戲截圖量過）
    wood = (64, 42, 26) if white else (176, 118, 66)
    ink = (235, 235, 235) if white else (24, 22, 20)
    per_row = per_row or len(all_lines)
    rows = (len(all_lines) + per_row - 1) // per_row
    label_h = 40 if labels else 0
    img = Image.new("RGB", (per_row * BOARD_W * S + 40, rows * (BH * S + label_h + 20) + 20), (244, 242, 238))
    d = ImageDraw.Draw(img)
    try:
        F = ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", 24)
    except OSError:
        F = None
    for k, lines in enumerate(all_lines):
        ox = 20 + (k % per_row) * BOARD_W * S
        oy = 20 + (k // per_row) * (BH * S + label_h + 20)
        d.rectangle([ox, oy, ox + BOARD_W * S - 1, oy + BH * S - 1], fill=wood, outline=tuple(max(0, v - 45) for v in wood), width=3)
        for r, ln in enumerate(lines):
            x = (BOARD_W - width(ln)) / 2
            y = TOP + r * PITCH
            for c in ln:
                if c == " ":
                    x += HALF; continue
                gx, gy = ox + (x + 0.5) * S, oy + y * S     # 8 寬的字畫在 9 寬格子的中間
                for q, on in enumerate(QUAD[c]):       # 左上、右上、左下、右下
                    if on:
                        qx, qy = gx + (q % 2) * 4 * S, gy + (q // 2) * 4 * S
                        d.rectangle([round(qx), round(qy), round(qx + 4 * S) - 1, round(qy + 4 * S) - 1], fill=ink)
                x += FULL
        if labels:
            d.text((ox + 10, oy + BH * S + 6), labels[k], font=F, fill=(90, 90, 90))
    img.save(dst)

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--png")
    ap.add_argument("--upper", action="store_true")
    ap.add_argument("--white", action="store_true")
    ap.add_argument("--sheet")
    ap.add_argument("--center", action="store_true", help="整排置中（預設靠左）")
    ap.add_argument("--boards", type=int, help="置中時指定用幾塊板子")
    a = ap.parse_args()
    if a.sheet:
        groups = ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZ",
                  "abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz",
                  "012", "345", "678", "9.,", "!?-", ":'"]
        render([build_board(list(g), "center") for g in groups], a.sheet, labels=groups, white=a.white, per_row=5)
        print("字母表：", a.sheet)
        return
    text = a.text.upper() if a.upper else a.text
    bad = sorted(set(c for c in text if c not in FONT))
    if bad:
        print("字母表裡還沒有這些字：", " ".join(repr(c) for c in bad)); sys.exit(1)
    boards, breaks, lines, off = layout(text, a.center, a.boards)
    print(f"「{text}」共 {len(boards)} 塊告示牌，由左到右貼在相鄰的方塊上。")
    if not a.center:
        print("排法：靠左（空的位置都在最右邊那塊）。")
    elif abs(off) < 2.5:
        print("排法：置中（第 1 塊的字靠右、最後一塊靠左，左右空白一樣）。")
    else:
        side = "右" if off > 0 else "左"
        print(f"排法：置中，但整排偏{side}約 {abs(off):.0f}（一個字約 31，等於偏{side}半個字左右）。"
              f"用 --boards {len(boards) + 1} 多一塊板子通常就能正中間。")
    if breaks:
        print("單字在這些板子之間換：" + "、".join(f"第 {i} 和第 {i+1} 塊" for i in breaks) + "（想看出空格可以中間空一個方塊）")
    for i, (b, ls) in enumerate(zip(boards, lines)):
        assert all(width(l) <= LIMIT for l in ls), "有一行超過 89"
        print(f"\n第 {i+1} 塊：{' '.join(b)}（寬 {' / '.join(str(width(l)) for l in ls)}）")
        print("```")
        print("\n".join(ls))
        print("```")
    if a.png:
        render(lines, a.png, labels=[f"第 {i+1} 塊" for i in range(len(lines))], white=a.white)
        print("\n預覽圖：", a.png)

if __name__ == "__main__":
    main()
