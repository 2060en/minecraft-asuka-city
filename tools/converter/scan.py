"""只讀不寫的掃描：列出世界裡用了哪些自製內容，以及 addon/mapping.json 有沒有漏登記。

用法（第一次先照 requirements.txt 裝好環境，見 docs/addon.md 的「轉換程式」）：

    tools/converter/.venv/Scripts/python.exe tools/converter/scan.py CX198
    tools/converter/.venv/Scripts/python.exe tools/converter/scan.py CX198 --json 報告.json

參數可以是世界的名稱（levelname.txt，要完全相同）或世界資料夾的路徑。

世界本體絕對不開：LevelDB 光是打開就可能寫入檔案，所以先把 db 複製到暫存資料夾，
只開那份副本，結束就刪掉；遊戲開著時拒絕執行，避免複製到寫到一半的資料。
結束前核對世界本體的檔案清單、大小與修改時間，確認完全沒變。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

from world import CUSTOM, CUSTOM_BYTES, cell_position, load_mapping, parse_key, parse_subchunk, read_all_nbt, read_nbt, walk_custom

REPO = Path(__file__).resolve().parents[2]
DIMS = {0: "主世界", 1: "地獄", 2: "終界"}
NAME = re.compile(rb"asukatech:[a-z0-9_]+")


def find_world(arg):
    path = Path(arg)
    if (path / "db").is_dir():
        return path
    users = Path(os.environ.get("APPDATA", "")) / "Minecraft Bedrock" / "Users"
    found = [p.parent for p in users.glob("*/games/com.mojang/minecraftWorlds/*/levelname.txt")
             if p.read_text(encoding="utf-8", errors="replace").strip() == arg]
    if len(found) != 1:
        raise SystemExit(f"名稱是「{arg}」的世界找到 {len(found)} 個：{[str(p) for p in found]}")
    return found[0]


def game_running():
    if sys.platform != "win32":
        return False
    return b"minecraft" in subprocess.run(["tasklist"], capture_output=True).stdout.lower()


def stop_if_game_uses(world):
    """遊戲開著就不碰遊戲資料夾裡的世界，才不會複製到寫到一半的資料。"""
    if "minecraftWorlds" in world.resolve().parts and game_running():
        raise SystemExit("遊戲正在執行，請先關閉遊戲再執行，才不會複製到寫到一半的資料。")


def new_report():
    return {
        "blocks": defaultdict(lambda: {"cells": 0, "by_dim": Counter(), "palette_subchunks": 0, "used_subchunks": 0, "positions": []}),
        "entities": defaultdict(lambda: {"count": 0, "positions": []}),
        "block_entity_items": [], "entity_items": [], "players": [],
        "other": defaultdict(lambda: {"count": 0, "names": set()}),
        "errors": [],
    }


def snapshot(db):
    """世界本體的檔案清單、大小與修改時間，用來確認掃描前後沒變。"""
    return {f.name: (f.stat().st_size, f.stat().st_mtime_ns) for f in db.iterdir()}


def scan_subchunk(value, where, blocks):
    kind, dim, cx, cz, sy = where
    for number, layer in enumerate(parse_subchunk(value)):
        custom = {i: e for i, e in enumerate(layer.palette) if e.get("name", "").startswith(CUSTOM)}
        if not custom:
            continue
        seen = set()
        for n, index in enumerate(layer.indices()):
            if index in custom:
                entry = custom[index]
                record = blocks[entry["name"]]
                record["cells"] += 1
                record["by_dim"][dim] += 1
                x, z, y = cell_position(n)
                record["positions"].append({"dim": dim, "x": cx * 16 + x, "y": sy * 16 + y, "z": cz * 16 + z,
                                            "layer": number, "states": entry.get("states", {})})
                seen.add(entry["name"])
        for name in {e["name"] for e in custom.values()}:   # 同一種方塊的不同狀態只算一次
            blocks[name]["palette_subchunks"] += 1
            if name in seen:
                blocks[name]["used_subchunks"] += 1


def scan(db, report):
    blocks, entities = report["blocks"], report["entities"]
    subchunks = keys = 0
    for key, value in db.iterate():
        keys += 1
        where = parse_key(key)
        kind = where[0] if where else None
        subchunks += kind == "subchunk"
        if CUSTOM_BYTES not in value:           # 絕大多數資料到這裡就跳過，所以整張地圖也很快
            continue
        try:
            if kind == "subchunk":
                scan_subchunk(value, where, blocks)
            elif key.startswith(b"actorprefix") or kind == "entity_old":
                for actor in ([read_nbt(value)[1]] if key.startswith(b"actorprefix") else read_all_nbt(value)):
                    identifier = actor.get("identifier", "")
                    pos = actor.get("Pos")
                    if identifier.startswith(CUSTOM):
                        entities[identifier]["count"] += 1
                        entities[identifier]["positions"].append(pos)
                    elif any(walk_custom(actor)):
                        report["entity_items"].append({"id": identifier, "pos": pos, "names": sorted(set(walk_custom(actor)))})
            elif kind == "block_entity":
                for entity in read_all_nbt(value):
                    names = sorted(set(walk_custom(entity)))
                    if names:
                        report["block_entity_items"].append({"dim": where[1], "id": entity.get("id"), "x": entity.get("x"),
                                                             "y": entity.get("y"), "z": entity.get("z"), "names": names})
            elif key == b"~local_player" or key.startswith(b"player_"):
                names = Counter(walk_custom(read_nbt(value)[1]))
                report["players"].append({"key": key.decode("ascii", errors="replace"), "names": dict(names)})
            else:
                label = kind or key.decode("ascii", errors="replace").split("_")[0][:24]
                other = report["other"][label]
                other["count"] += 1
                other["names"].update(m.decode() for m in NAME.findall(value))
        except Exception as e:                  # 記下來繼續掃，最後報告會標明不完整
            report["errors"].append({"key": key.hex(), "kind": kind, "error": repr(e)})
    report["keys"], report["subchunks"] = keys, subchunks


def show(report, known_blocks, known_entities):
    print(f"掃描：{report['subchunks']:,} 個區段、共 {report['keys']:,} 筆資料，用時 {report['seconds']:.0f} 秒\n")

    print("【自製方塊】實際格數看索引，不是只看調色盤；「調色盤」是列出這種方塊的區段數")
    for name, r in sorted(report["blocks"].items()):
        dims = "、".join(f"{DIMS.get(d, d)} {c}" for d, c in sorted(r["by_dim"].items())) or "－"
        mark = "已登記" if name in known_blocks else "★沒有登記"
        print(f"  {name:32} {r['cells']:>6} 格｜調色盤 {r['palette_subchunks']:>3}｜實際用到 {r['used_subchunks']:>3}｜{dims}｜{mark}")
    if not report["blocks"]:
        print("  （沒有）")

    print("\n【自製實體】")
    for name, r in sorted(report["entities"].items()):
        mark = "已登記" if name in known_entities else "★沒有登記"
        print(f"  {name:32} {r['count']:>6} 個｜{mark}")
    if not report["entities"]:
        print("  （沒有）")

    print("\n【容器與物品框架裡的自製物品】（方塊實體）")
    for item in report["block_entity_items"]:
        print(f"  {item['id']} ({item['x']}, {item['y']}, {item['z']})：{'、'.join(item['names'])}")
    if not report["block_entity_items"]:
        print("  （沒有）")

    print("\n【其他實體身上的自製物品】（掉在地上的物品、盔甲座等）")
    for item in report["entity_items"]:
        print(f"  {item['id']} {item['pos']}：{'、'.join(item['names'])}")
    if not report["entity_items"]:
        print("  （沒有）")

    print("\n【玩家物品欄裡的自製物品】")
    for player in report["players"]:
        print(f"  {player['key']}：" + "、".join(f"{k} × {v}" for k, v in sorted(player["names"].items())))
    if not report["players"]:
        print("  （沒有）")

    print("\n【其他資料裡出現的自製識別碼】（結構、排程中的方塊更新等）")
    for label, r in sorted(report["other"].items()):
        print(f"  {label}：{r['count']} 筆，{'、'.join(sorted(r['names']))}")
    if not report["other"]:
        print("  （沒有）")

    unknown_blocks = [n for n, r in report["blocks"].items() if n not in known_blocks]
    unknown_entities = [n for n in report["entities"] if n not in known_entities]
    print("\n【沒有登記的東西】")
    for name in sorted(unknown_blocks):
        r = report["blocks"][name]
        if r["cells"]:
            sample = "、".join(f"{DIMS.get(p['dim'], p['dim'])} ({p['x']}, {p['y']}, {p['z']})" for p in r["positions"][:10])
            print(f"  方塊 {name}：{r['cells']} 格，例如 {sample}")
        else:
            print(f"  方塊 {name}：實際 0 格，只留在 {r['palette_subchunks']} 個區段的調色盤裡")
    for name in sorted(unknown_entities):
        sample = "、".join(str([round(v, 1) for v in p]) for p in report["entities"][name]["positions"][:10] if p)
        print(f"  實體 {name}：{report['entities'][name]['count']} 個，例如 {sample}")
    if not unknown_blocks and not unknown_entities:
        print("  （沒有）")

    if report["errors"]:
        print(f"\n【解析錯誤】{len(report['errors'])} 筆，這份報告不完整：")
        for error in report["errors"][:10]:
            print(f"  {error['kind']} {error['key']}：{error['error']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="只讀不寫的掃描，只開世界的副本")
    parser.add_argument("world", help="世界的名稱或資料夾路徑")
    parser.add_argument("--json", help="把完整結果（含每一格的座標）存成這個檔案")
    args = parser.parse_args()

    world = find_world(args.world)
    source = world / "db"
    stop_if_game_uses(world)
    print(f"世界：{(world / 'levelname.txt').read_text(encoding='utf-8', errors='replace').strip()}（{world}）")

    need = sum(f.stat().st_size for f in source.iterdir())
    temp_root = Path(tempfile.gettempdir())
    if shutil.disk_usage(temp_root).free < need * 2:
        raise SystemExit(f"暫存資料夾所在的磁碟空間不夠，至少要 {need * 2 / 1e9:.1f} GB。")

    import leveldb                              # 放在這裡：環境沒裝好時，前面的檢查還是能跑

    known_blocks, known_entities = load_mapping(REPO / "addon" / "mapping.json")
    report = new_report()
    before = snapshot(source)
    temp = Path(tempfile.mkdtemp(prefix="asuka_scan_"))
    try:
        print(f"複製 db（{need / 1e9:.2f} GB）到暫存資料夾…")
        shutil.copytree(source, temp / "db")
        started = time.time()
        db = leveldb.LevelDB(str(temp / "db"), create_if_missing=False)
        try:
            scan(db, report)
        finally:
            db.close()
        report["seconds"] = time.time() - started
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    show(report, known_blocks, known_entities)
    same = snapshot(source) == before
    print(f"\n世界本體：{'檔案清單、大小與修改時間都沒變' if same else '★掃描前後不同，請檢查是不是遊戲或其他程式動過'}")

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1, default=sorted), encoding="utf-8")
        print(f"完整結果：{args.json}")
    sys.exit(1 if report["errors"] or not same else 0)


if __name__ == "__main__":
    main()
