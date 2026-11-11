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

def block_mask(c):
    """方塊字家族（U+2580～259F）在 8×8 單位格子裡的形狀，值是覆蓋率 0～1；不是方塊字回傳 None。
    2026-11-12 跟遊戲字型圖逐格對過：▁～▇ 是下緣 1/8～7/8 高、▉～▏ 是左緣 7/8～1/8 寬、
    ▔ 頂端 1/8、▕ 右緣 1/8、░▒▓ 是 1/4、1/2、3/4 的網點。"""
    cp = ord(c)
    if c in QUAD and c != ".":
        q = QUAD[c]
        return [[q[(y >= 4) * 2 + (x >= 4)] for x in range(8)] for y in range(8)]
    if 0x2581 <= cp <= 0x2587:
        k = cp - 0x2580
        return [[1 if y >= 8 - k else 0 for x in range(8)] for y in range(8)]
    if 0x2589 <= cp <= 0x258F:
        k = 8 - (cp - 0x2588)
        return [[1 if x < k else 0 for x in range(8)] for y in range(8)]
    if 0x2591 <= cp <= 0x2593:
        return [[(cp - 0x2590) / 4] * 8 for y in range(8)]
    if cp == 0x2594:
        return [[1 if y == 0 else 0 for x in range(8)] for y in range(8)]
    if cp == 0x2595:
        return [[1 if x == 7 else 0 for x in range(8)] for y in range(8)]
    return None

BLOCKS = [chr(cp) for cp in range(0x2580, 0x25A0) if block_mask(chr(cp))]

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
    # 漢字、假名（2026-11-12 作者要「中華そば」）：比英文寬，一塊板子放一個字、置中。
    # 直筆用整格 █、橫筆用半格 ▀▄，粗細跟英文字母一樣；告示牌上下行之間的縫剛好把相鄰的橫筆分開。
    # 新的字先畫 8 行的小方塊圖（筆畫對齊兩欄一格），用 from_bitmap() 換成這裡的寫法。
    "中": "▄▄▄█▄▄▄ █..█..█ ▀▀▀█▀▀▀ ...█...",   # 7 格，跟華一樣寬（作者 2026-11-12）
    "華": "▄█▄▄▄█▄ ▀▜▀█▀▛▀ ▀▜▀█▀▛▀ ▀▀▀█▀▀▀",   # 兩側直筆變細；三根一樣粗的版本是 "▄█▄▄▄█▄ ▀█▀█▀█▀ ▀█▀█▀█▀ ▀▀▀█▀▀▀"（像「井」）
    "そ": ".▀▀█▀ ▄▄█▄▄ .▄▀.. .▀▄▄▄",
    "ば": "▄...█▐▐ █..▀█▀. █.▄▄█.. ▀.█▄▄▀▄",
    # 書法風「春水堂」（2026-11-12）：預設是標楷體自動轉換、只用整格字的版本，其他版本在下面的 STYLES。
    "春": ".▂▟▄.. .▂█▄▄. ▂▞▄█▚▃ ..▙▟..",   # 「日」補上左半邊（作者 2026-11-12）
    "水": "..▜.▁. ▄▅▟▞▔. ▂▀▜▀▄▁ ..▇..▔",
    "堂": ".▃▜... ▟▀▂▃▔▀ ..▆▀.. .▃▟▄▅.",
}
# 同一個字的其他寫法，用 --style 切換（會蓋掉 FONT 裡同名的字）
STYLES = {
    # 標楷體自動轉換：python 字型轉方塊.py 春水堂 --font kaiu.ttf --cells 8 --stretch 1.4 --bold 0.5
    # 作者 2026-11-12 從五種字型的比較圖裡圈了這組「感覺不錯」。
    # 「楷書」只用整格字（現在的預設）；「楷書含半邊」是當時那組，用了 ▏▎▐▝ 等半邊字，作者蓋出來歪掉
    "楷書": {"春": ".▂▟▄.. .▂█▄▄. ▂▞▄█▚▃ ..▙▟..",   # 「日」補上左半邊（作者 2026-11-12）
             "水": "..▜.▁. ▄▅▟▞▔. ▂▀▜▀▄▁ ..▇..▔",
             "堂": ".▃▜... ▟▀▂▃▔▀ ..▆▀.. .▃▟▄▅."},
    "楷書含半邊": {"春": ".▂▟▄.. .▂█▄▄. ▂▝▏▜▚▃ .▕▏▟..",
                  "水": "..▐▎▁. ▗▅▟▖▘. ▗▘▐▝▄▁ ..▇..▔",
                  "堂": ".▃▐▗▎. ▟▀▂▃▔▘ .▕▆▀.. ▗▃▟▄▅."},
    # 隸書第一版：參考隸書手工畫，9 格寬、長橫起筆細收筆粗上翹（蠶頭燕尾）。作者蓋了：「有一點形狀但不夠好」
    "隸書一": {"春": "..▃▃█▃▄.. .▀▀▛▀▜▀▀. ▁▂▟▃▃▃▙▅▇ ...▐▃▌...",
               "水": "....█..▄. .▀▀▜.█▞.. ▁▟▘.█.▚▄▇ ...▄█....",
               "堂": "..▗.█.▖.. ▛▀▀▀▀▀▀▀▜ ...▛▀▜... ▁▂▃▃█▃▃▅▇"},
    # 隸書第二版：收窄到 7 格、筆畫加粗、撇捺用斜方塊接。作者：「怪怪的，還不如上一版」
    "隸書二": {"春": ".▄▄█▄▄. ▀▀▀█▀▀▀ ▄▄▟█▙▄▄ ▂▀▐█▌▀▆",
               "水": "...█.▖. ▀▀▜█▞.. .▞.█▚.. ▝.▄█.▀▆",
               "堂": ".▚.█.▞. ▛▀▀▀▀▀▜ .▛▀█▀▜. ▄▄▄█▄▄▆"},
}

WIDE = 5   # 寬到 5 格以上的字（漢字、假名）一塊板子只放一個、置中

def from_bitmap(rows):
    """把 8 行的小方塊圖（"#" 有、"." 沒有，每兩欄是一格）換成 FONT 的寫法。設計新漢字時用：
    print(from_bitmap(["....", ...]))，再把結果貼進 FONT。"""
    rev = {v: k for k, v in QUAD.items()}
    w = max(len(r) for r in rows); w += w % 2
    rows = [r.ljust(w, ".") for r in rows]
    return " ".join("".join(rev[(rows[2 * L][c] == "#", rows[2 * L][c + 1] == "#",
                                 rows[2 * L + 1][c] == "#", rows[2 * L + 1][c + 1] == "#")]
                            for c in range(0, w, 2)) for L in range(4))

# 符號：作者在遊戲裡確認過的現成寫法，照原樣輸出（空白也是調過的，不能動），每個符號自己佔一塊板子。
# 照截圖抄的符號加在這裡；要用四分之一方塊重新設計、讓程式自動對齊的，加進上面的 FONT。
SYMBOLS = {
    "↑": ("往上：AKQ 出発口大箭頭（2026-11-11 蓋好）", ["▟▙", "▟██▙", "▀▀██▀▀", "██"]),
    "←": ("往左：實心小頭＋細箭桿（AKQ 北端立牌）", ["  ▟      ", "▟█▄▄▄", "▜█▀▀▀", "  ▜      "]),
    "→": ("往右：往左的左右翻過來（AKQ 北端電梯前立牌）", ["      ▙  ", "▄▄▄█▙", "▀▀▀█▛", "      ▛  "]),
    "↙": ("往左下：作者改過的標準寫法（AKQ 北端樓梯口立牌）", ["     ▞", "█  ▞   ", "█▞     ", "▇▇▇   "]),
    "↘": ("往右下：往左下的左右翻過來", ["▚     ", "   ▚  █", "     ▚█", "   ▇▇▇"]),
    "🏃": ("逃生出口的跑步小人：一般英文符號拼的（像素字型），照 NextGamer 影片的 Java 版，基岩版字寬一樣",
          ["_o", "//\\_", "_/\\    ", "/ "]),
    # 印章（2026-11-12 作者要在春水堂前面加紅色印章）：實心紅方塊、中間刻出白色菱形花紋、四角缺口，只用整格字；
    # 每行開頭的 §4 是深紅色代碼（不顯示、不佔寬度）。跟字一樣高；比字小的版本 ▄▄▄／▙▀▟／▛▄▜／▀▀▀ 太空、像方框，沒用
    "㊞": ("紅色印章：§4 深紅，實心方塊刻白色菱形花紋", ["§4▛██▜", "§4█▞▚█", "§4█▚▞█", "§4▙██▟"]),
}

# 基岩版的顏色代碼：§ 加一個字，不顯示、不佔寬度，後面的字換成這個顏色（每行開頭都要再打一次比較保險）
COLOR_CODES = {"0": (0, 0, 0), "1": (0, 0, 170), "2": (0, 170, 0), "3": (0, 170, 170), "4": (170, 0, 0),
               "5": (170, 0, 170), "6": (255, 170, 0), "7": (170, 170, 170), "8": (85, 85, 85), "9": (85, 85, 255),
               "a": (85, 255, 85), "b": (85, 255, 255), "c": (255, 85, 85), "d": (255, 85, 255), "e": (255, 255, 85),
               "f": (255, 255, 255), "g": (221, 214, 5), "m": (151, 22, 7), "p": (222, 177, 45), "q": (71, 160, 54)}

def strip_codes(s):
    """拿掉 §x 顏色代碼（遊戲裡不顯示、不佔寬度）"""
    out, i = "", 0
    while i < len(s):
        if s[i] == "§" and i + 1 < len(s):
            i += 2; continue
        out += s[i]; i += 1
    return out

# 像素字型（一整行都是一般英文符號時）的字寬，從遊戲字型量的（最右欄＋2），基岩版和 Java 版一樣
ASCII_W = {' ': 4, '!': 2, '"': 4, '#': 6, '$': 6, '%': 6, '&': 6, "'": 2, '(': 4, ')': 4, '*': 4, '+': 6,
           ',': 2, '-': 6, '.': 2, '/': 6, ':': 2, ';': 2, '<': 5, '=': 6, '>': 5, '?': 6, '@': 7,
           'I': 4, '[': 4, '\\': 6, ']': 4, '^': 6, '_': 6, '`': 3, 'f': 5, 'i': 2, 'k': 5, 'l': 3,
           't': 4, '{': 4, '|': 2, '}': 4, '~': 7}   # 沒列出來的英文字母和數字都是 6

def is_pixel_line(s):
    return all(0x20 <= ord(c) <= 0x7e for c in s)

def glyph(ch):
    rows = FONT[ch].split(" ")
    assert len(rows) == 4 and len({len(r) for r in rows}) == 1, f"字母 {ch!r} 的 4 行格數不一樣"
    for r in rows:
        for c in r:
            assert c == "." or block_mask(c), f"字母 {ch!r} 用了方塊字家族以外的字 {c!r}"
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
    if len(chs) == 1 and len(glyph(chs[0])[0]) >= WIDE:   # 漢字、假名一塊一個字，一律置中
        align = "center"
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
    """一行在告示牌上的寬度：整行都是一般英文符號 → 像素字型；混了別的字 → 等寬字型（半形 4、全形 9）。§ 顏色代碼不算"""
    line = strip_codes(line)
    if is_pixel_line(line):
        return sum(ASCII_W.get(c, 6) for c in line)
    return sum(HALF if ord(c) < 0x1100 else FULL for c in line)

def split_items(text):
    """把要寫的字拆成「文字段」和「符號」：[("seg", 文字) 或 ("sym", 符號)]"""
    items, cur = [], ""
    for ch in text:
        if ch in SYMBOLS:
            if cur.strip():
                items.append(("seg", cur.strip()))
            items.append(("sym", ch)); cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(("seg", cur.strip()))
    return items

def layout(text, center=False, n_boards=None):
    """回傳（板子, 換單字處, 每塊的 4 行, 偏移）。板子是字母清單，或是一個符號（字串）。
    只有文字時照 center 靠左或置中；有符號時，每個符號自己一塊，旁邊的文字靠向符號那一邊。"""
    items = split_items(text)
    if not any(k == "sym" for k, _ in items):
        return layout_seg(items[0][1] if items else "", "center" if center else "left", n_boards)
    boards, breaks, lines = [], [], []
    for i, (kind, v) in enumerate(items):
        if kind == "sym":
            boards.append(v); lines.append(list(SYMBOLS[v][1])); continue
        left = i > 0 and items[i - 1][0] == "sym"
        right = i + 1 < len(items) and items[i + 1][0] == "sym"
        b, br, ls, _ = layout_seg(v, "center" if (left and right) else "left" if left else "right")
        breaks += [len(boards) + x for x in br]
        boards += b; lines += ls
    return boards, breaks, lines, 0

def layout_seg(text, mode, n_boards=None):
    """一段文字分板子。mode：
    left 靠左：盡量塞滿，最後一塊靠左，空的都在右邊。
    right 靠右：從後面塞滿，第 1 塊靠右，空的都在左邊（文字右邊接著符號時用）。
    center 置中：第 1 塊靠右、最後一塊靠左、中間照常；試各種「第 1 塊放幾個字」，挑左右空白最接近的。
      偏移＝整排字往右偏多少（告示牌單位，31 約一個字）；n_boards 可以指定用幾塊（多一塊常常就能正中間）。"""
    if mode == "left":
        boards, breaks = pack(text)
        n = len(boards)
        aligns = ["left"] if n == 1 else ["center"] * (n - 1) + ["left"]
        return boards, breaks, [build_board(b, a) for b, a in zip(boards, aligns)], 0
    if mode == "right":
        rb, rbr = pack(text[::-1])
        n = len(rb)
        boards = [list(reversed(b)) for b in reversed(rb)]
        breaks = sorted(n - i for i in rbr)
        aligns = ["right"] + ["center"] * (n - 1)
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
    base_ink = (235, 235, 235) if white else (24, 22, 20)
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
            pixel = is_pixel_line(strip_codes(ln))
            ink = base_ink
            chars = list(ln); i = -1
            while i + 1 < len(chars):
                i += 1; c = chars[i]
                if c == "§" and i + 1 < len(chars):     # 顏色代碼：換顏色，不畫、不佔寬度
                    ink = COLOR_CODES.get(chars[i + 1], base_ink) if chars[i + 1] != "r" else base_ink
                    i += 1; continue
                if pixel:                              # 像素字型：位置照字寬算，字形只畫示意
                    w = ASCII_W.get(c, 6)
                    if c != " ":
                        draw_ascii(d, c, ox + x * S, oy + y * S, (w - 1) * S, S, ink)
                    x += w; continue
                if c == " ":
                    x += HALF; continue
                gx, gy = ox + (x + 0.5) * S, oy + y * S     # 8 寬的字畫在 9 寬格子的中間
                m = block_mask(c)
                if m:                                       # 方塊字家族：照 8×8 形狀畫；網點用顏色深淺表示
                    for yy in range(8):
                        for xx in range(8):
                            v = m[yy][xx]
                            if v:
                                col = ink if v >= 1 else tuple(round(w * (1 - v) + k * v) for w, k in zip(wood, ink))
                                d.rectangle([round(gx + xx * S), round(gy + yy * S), round(gx + (xx + 1) * S) - 1, round(gy + (yy + 1) * S) - 1], fill=col)
                else:                                       # 其他字：畫個框表示這裡有字
                    d.rectangle([round(gx), round(gy), round(gx + 8 * S) - 1, round(gy + 8 * S) - 1], outline=ink, width=2)
                x += FULL if ord(c) >= 0x1100 else HALF
        if labels:
            d.text((ox + 10, oy + BH * S + 6), labels[k], font=F, fill=(90, 90, 90))
    img.save(dst)

def draw_ascii(d, c, x, y, w, S, ink):
    """像素字型的示意字形（只為了看位置；不附遊戲字型檔）。字高 8，第 7 列是底線。"""
    lw = max(2, S // 2)
    if c == "/":
        d.line([(x, y + 7 * S), (x + w, y)], fill=ink, width=lw)
    elif c == "\\":
        d.line([(x, y), (x + w, y + 7 * S)], fill=ink, width=lw)
    elif c == "_":
        d.rectangle([x, y + 7 * S, x + w, y + 8 * S - 1], fill=ink)
    elif c == "o":
        d.ellipse([x, y + 2.5 * S, x + w, y + 7 * S], outline=ink, width=lw)
    elif c == "-":
        d.rectangle([x, y + 3.5 * S, x + w, y + 4.5 * S], fill=ink)
    elif c in "|!":
        d.rectangle([x, y, x + S, y + 7 * S], fill=ink)
    else:
        d.rectangle([x, y, x + w, y + 7 * S], outline=ink, width=lw)

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
    ap.add_argument("--list", action="store_true", help="列出可以用的符號")
    ap.add_argument("--style", help="字的其他寫法，例如：" + "、".join(STYLES))
    a = ap.parse_args()
    if a.style:
        if a.style not in STYLES:
            sys.exit("沒有這個風格，可以用：" + "、".join(STYLES))
        FONT.update(STYLES[a.style])
    if a.list:
        for k, (desc, _) in SYMBOLS.items():
            print(k, desc)
        return
    if a.sheet:
        groups = ["ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZ",
                  "abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz",
                  "012", "345", "678", "9.,", "!?-", ":'"] + [k for k in FONT if len(glyph(k)[0]) >= WIDE]
        boards = [build_board(list(g), "center") for g in groups] + [list(v[1]) for v in SYMBOLS.values()]
        render(boards, a.sheet, labels=groups + [{"🏃": "跑步小人"}.get(k, k) for k in SYMBOLS], white=a.white, per_row=5)
        print("字母表：", a.sheet)
        return
    text = a.text.upper() if a.upper else a.text
    bad = sorted(set(c for c in text if c not in FONT and c not in SYMBOLS))
    if bad:
        print("字母表裡還沒有這些字：", " ".join(repr(c) for c in bad)); sys.exit(1)
    boards, breaks, lines, off = layout(text, a.center, a.boards)
    has_sym = any(isinstance(b, str) for b in boards)
    print(f"「{text}」共 {len(boards)} 塊告示牌，由左到右貼在相鄰的方塊上。")
    text_boards = [b for b in boards if not isinstance(b, str)]
    all_wide = bool(text_boards) and all(len(b) == 1 and len(glyph(b[0])[0]) >= WIDE for b in text_boards)
    if has_sym and all_wide:
        print("排法：每個符號、每個漢字各自一塊，每塊置中。")
    elif has_sym:
        print("排法：每個符號自己一塊；旁邊的文字靠向符號那一邊。")
    elif all_wide:
        print("排法：漢字、假名一塊一個字，每塊置中（不用選靠左或置中）。")
    elif not a.center:
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
        what = f"符號 {b}（{SYMBOLS[b][0]}）" if isinstance(b, str) else " ".join(b)
        print(f"\n第 {i+1} 塊：{what}（寬 {' / '.join(str(width(l)) for l in ls)}）")
        print("```")
        print("\n".join(ls))
        print("```")
    if a.png:
        render(lines, a.png, labels=[f"第 {i+1} 塊" for i in range(len(lines))], white=a.white)
        print("\n預覽圖：", a.png)

if __name__ == "__main__":
    main()
