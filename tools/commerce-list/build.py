"""把 docs/world/commerce.md 的「品牌與店家一覽」做成一頁 HTML 清單。

用法：
    python3 tools/commerce-list/build.py          # 產生清單，「新」照上次 --save 時的狀態標
    python3 tools/commerce-list/build.py --save   # 產生清單，並記下這次的狀態（每次回覆作者時用這個）

輸出：tools/commerce-list/out/commerce-list.html（不進 repo）。
上次 --save 之後新增的項目會標「新」，狀態記在 out/state.json。
"""

import datetime
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "world" / "commerce.md"
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT = OUT_DIR / "commerce-list.html"
STATE = OUT_DIR / "state.json"

CATEGORY_STYLE = {"一": "c1", "二": "c2", "三": "c3"}


def section(lines, title):
    """回傳某個二級標題底下的行，到下一個二級標題為止。"""
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.strip() == f"## {title}"
            continue
        if inside:
            out.append(line)
    return out


def inline(text):
    """把一格的 markdown 轉成 HTML：連結只留文字，粗體、程式碼照樣。"""
    text = html.escape(text.strip(), quote=False)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def plain(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"[*`]", "", text).strip()


def cells(line):
    return [c for c in line.strip().strip("|").split("|")]


def parse_brands(lines):
    """回傳 [(類別標題, [(小標題, 表頭, [列])])]。"""
    categories, cat, sub = [], None, None
    table = []

    def flush():
        nonlocal table
        if cat is not None and len(table) >= 2:
            header = [plain(c) for c in cells(table[0])]
            rows = [cells(r) for r in table[2:]]
            cat[1].append((sub, header, rows))
        table = []

    for line in lines:
        if line.startswith("### "):
            flush()
            cat = (line[4:].strip(), [])
            categories.append(cat)
            sub = None
        elif line.startswith("#### "):
            flush()
            sub = line[5:].strip()
        elif line.startswith("|"):
            table.append(line)
        else:
            flush()
    flush()
    return categories


def parse_pending(lines):
    items = []
    for line in lines:
        if line.startswith("### 已決定"):
            break
        m = re.match(r"- \[ \] \*\*(.+?)\*\*(.*)", line)
        if m:
            items.append(plain(m.group(1)))
    return items


def load_state(current):
    if not STATE.exists():
        return {"base": sorted(current), "last": sorted(current)}
    return json.loads(STATE.read_text(encoding="utf-8"))


def main():
    save = "--save" in sys.argv[1:]
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    categories = parse_brands(section(lines, "品牌與店家一覽"))
    pending = parse_pending(section(lines, "待決定事項"))

    keys = {}
    for cat_title, tables in categories:
        for sub, _, rows in tables:
            for row in rows:
                keys[(cat_title, sub, plain(row[0]))] = True
    current = {" / ".join(filter(None, k)) for k in keys}

    state = load_state(current)
    if save and sorted(current) != state["last"]:
        state = {"base": state["last"], "last": sorted(current)}
    base = set(state["base"])

    tz = datetime.timezone(datetime.timedelta(hours=8))
    now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    body = []
    summary = []
    for cat_title, tables in categories:
        cls = CATEGORY_STYLE.get(cat_title[:1], "c1")
        count = sum(len(rows) for _, _, rows in tables)
        new_count = 0
        parts = []
        for sub, header, rows in tables:
            trs = []
            for row in rows:
                key = " / ".join(filter(None, (cat_title, sub, plain(row[0]))))
                is_new = key not in base
                new_count += is_new
                tds = []
                for i, c in enumerate(row):
                    content = inline(c)
                    label = html.escape(header[i]) if i < len(header) else ""
                    if i == 0:
                        badge = '<span class="new">新</span>' if is_new else ""
                        tds.append(f'<td class="name">{content}{badge}</td>')
                    else:
                        short = " class=\"short\"" if len(plain(c)) <= 8 else ""
                        tds.append(f'<td data-label="{label}"{short}>{content}</td>')
                trs.append(f'<tr class="{"is-new" if is_new else ""}">{"".join(tds)}</tr>')
            ths = "".join(f"<th>{html.escape(h)}</th>" for h in header)
            heading = f"<h3>{html.escape(sub)}<span class=\"n\">{len(rows)}</span></h3>" if sub else ""
            parts.append(
                f'{heading}<div class="scroll"><table><thead><tr>{ths}</tr></thead>'
                f'<tbody>{"".join(trs)}</tbody></table></div>'
            )
        new_note = f'<span class="chip-new">新 {new_count}</span>' if new_count else ""
        summary.append(
            f'<a class="chip {cls}" href="#{cls}"><b>{html.escape(cat_title)}</b>'
            f'<span>{count} 項</span>{new_note}</a>'
        )
        body.append(
            f'<section id="{cls}" class="cat {cls}"><h2>{html.escape(cat_title)}'
            f'<span class="n">{count}</span></h2>{"".join(parts)}</section>'
        )

    pending_html = "".join(f"<li>{html.escape(p)}</li>" for p in pending)

    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>津蘭的商家與品牌</title>
<style>
:root {{
  --bg: #f6f5f2; --card: #ffffff; --ink: #1d1d1f; --sub: #6b6b70; --line: #e4e2dc;
  --c1: #2f6db5; --c2: #7a3db8; --c3: #b5701f; --new: #d6336c;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #161618; --card: #202023; --ink: #ededee; --sub: #a0a0a6; --line: #34343a;
    --c1: #6aa5ec; --c2: #b98ae6; --c3: #e3a75a; --new: #ff6b9a;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.6 -apple-system, "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
}}
main {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }}
header h1 {{ font-size: 22px; margin: 0 0 4px; letter-spacing: .02em; }}
header p {{ margin: 0; color: var(--sub); font-size: 13px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 8px; }}
.chip {{
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 10px;
  background: var(--card); border: 1px solid var(--line); color: var(--ink); text-decoration: none;
  border-left: 4px solid var(--accent);
}}
.chip span {{ color: var(--sub); font-size: 13px; }}
.chip .chip-new {{ color: var(--new); font-weight: 600; }}
.c1 {{ --accent: var(--c1); }} .c2 {{ --accent: var(--c2); }} .c3 {{ --accent: var(--c3); }}
.cat {{
  background: var(--card); border: 1px solid var(--line); border-top: 4px solid var(--accent);
  border-radius: 12px; padding: 4px 16px 12px; margin-top: 16px;
}}
h2 {{ font-size: 18px; margin: 12px 0 4px; color: var(--accent); }}
h3 {{ font-size: 14px; margin: 16px 0 6px; color: var(--sub); font-weight: 600; }}
.n {{
  display: inline-block; margin-left: 8px; padding: 0 7px; border-radius: 99px; font-size: 12px;
  background: var(--line); color: var(--sub); font-weight: 500; vertical-align: 2px;
}}
.scroll {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{
  text-align: left; font-weight: 600; color: var(--sub); font-size: 12px;
  border-bottom: 1px solid var(--line); padding: 6px 8px; white-space: nowrap;
}}
td {{ border-bottom: 1px solid var(--line); padding: 7px 8px; vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
td.name {{ font-weight: 600; white-space: nowrap; }}
tr.is-new td {{ background: color-mix(in srgb, var(--new) 7%, transparent); }}
.new {{
  display: inline-block; margin-left: 6px; padding: 0 6px; border-radius: 99px;
  background: var(--new); color: #fff; font-size: 11px; font-weight: 600; vertical-align: 1px;
}}
td:nth-child(2), td:nth-child(3) {{ white-space: nowrap; }}
code {{ font-size: 12px; }}
@media (max-width: 640px) {{
  main {{ padding: 16px 10px 40px; }}
  .cat {{ padding: 4px 12px 8px; }}
  table, tbody, tr, td {{ display: block; width: 100%; }}
  thead {{ display: none; }}
  tr {{ padding: 8px 0; border-bottom: 1px solid var(--line); }}
  tr:last-child {{ border-bottom: none; }}
  tr.is-new {{ background: color-mix(in srgb, var(--new) 7%, transparent); border-radius: 8px; padding: 8px; }}
  tr.is-new td {{ background: none; }}
  td {{ border: none; padding: 1px 0; white-space: normal !important; }}
  td.name {{ font-size: 15px; white-space: normal; }}
  td[data-label] {{ display: flex; gap: 10px; font-size: 13px; }}
  td[data-label]::before {{ content: attr(data-label); color: var(--sub); flex: 0 0 4.5em; }}
  td.short {{ display: inline-flex; width: auto; margin-right: 18px; }}
  td.short::before {{ flex: none; }}
}}
.pending {{ margin-top: 20px; color: var(--sub); }}
.pending h2 {{ color: var(--ink); font-size: 16px; }}
.pending ul {{ margin: 4px 0 0; padding-left: 20px; }}
</style>
</head>
<body>
<main>
<header>
<h1>津蘭的商家與品牌</h1>
<p>依 docs/world/commerce.md 產生 · {now}（台灣時間）· 標「新」的是上一份清單之後加的</p>
</header>
<nav class="chips">{"".join(summary)}</nav>
{"".join(body)}
<section class="pending"><h2>還沒定的</h2><ul>{pending_html}</ul></section>
</main>
</body>
</html>
"""
    OUT_DIR.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    if save:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
