"""轉換程式：把世界的副本轉成不需要附加內容的原味版，輸出成可以雙擊匯入的 .mcworld。

用法：
    tools/converter/.venv/Scripts/python.exe tools/converter/convert.py CX198

世界本體絕對不動，遊戲的世界資料夾也不寫入。流程：

1. 把世界複製到暫存資料夾，之後只動那份副本
2. 預檢：有對照表沒登記、實際又用到的東西，就停下來列出座標，什麼都不輸出
3. 轉換（規則見 docs/addon.md 的「轉換程式」）：
   - 自製方塊換成對照表上的原版方塊；沒有任何一格在用的舊名字直接清掉
   - 自製實體刪掉
   - 箱子、玩家物品欄等地方的自製物品刪掉
   - 待處理便條（pending_ticks 等）提到自製方塊的刪掉
4. 重新打開再掃一次，還有任何自製識別碼就停下來，不輸出
5. 世界改名成「<名稱> 原味版」、不啟用任何包，打包到 addon/build/worlds/
"""
import argparse
import shutil
import struct
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from scan import DIMS, find_world, new_report, scan, show, snapshot, stop_if_game_uses
from world import (CUSTOM, CUSTOM_BYTES, cell_position, load_mapping, pack_indices, parse_key, parse_subchunk, read_typed,
                   subchunk_head_size, write_layer, write_typed)

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "addon" / "build" / "worlds"
ACTOR = b"actorprefix"


class ConvertError(Exception):
    """碰到不能自己決定的資料：停下來，不輸出半成品。"""


def block_rule(blocks, name):
    rule = blocks[name]
    while "same_as" in rule:
        rule = blocks[rule["same_as"]]
    return rule


def vanilla_state(rule, states):
    """自製方塊的狀態換成原版的；對照表沒提到的（例如 powered）不帶過去。"""
    out = dict(rule.get("fixed_states", {}))
    for name, target in rule.get("states", {}).items():
        if name not in states:
            raise ConvertError(f"對照表要的狀態 {name} 在這一格沒有：{states}")
        if isinstance(target, str):
            out[target] = states[name]
        else:
            key = str(states[name])
            if key not in target["values"]:
                raise ConvertError(f"狀態 {name} 的值 {key} 對照表沒有")
            out[target["to"]] = target["values"][key]
    if rule.get("door_halves"):                 # 原版的門：下半存開關、門軸固定 0；上半存門軸、開關固定 0
        if out["upper_block_bit"]:
            out["open_bit"] = 0
        else:
            out["door_hinge_bit"] = 0
    return out


def palette_entry(name, states, version):
    """寫成和遊戲相同的調色盤項目（從真實存檔查的）：狀態照字母排序，_bit 是位元組，其他數字是整數。"""
    def typed(key, value):
        if isinstance(value, str):
            return (8, value)
        return (1, int(value)) if key.endswith("_bit") else (3, int(value))
    return write_typed("", (10, {"name": (8, name),
                                 "states": (10, {k: typed(k, states[k]) for k in sorted(states)}),
                                 "version": (3, version)}))


def frame_entity(x, y, z):
    """空的方塊實體，和遊戲自己存的空發光物品框架相同（從真實存檔查的）。"""
    return write_typed("", (10, {"BlockEntityVersion": (3, 0), "id": (8, "GlowItemFrame"),
                                 "x": (3, x), "y": (3, y), "z": (3, z)}))


def convert_subchunk(value, where, blocks):
    """回傳 (新的值, 要補的方塊實體, 每種方塊換了幾格, 清掉的舊名字)。"""
    _, _, cx, cz, sy = where
    layers = parse_subchunk(value)
    frames, counts, cleared = [], Counter(), Counter()
    for layer in layers:
        if not any(e.get("name", "").startswith(CUSTOM) for e in layer.palette):
            continue
        indices = list(layer.indices())
        used = Counter(indices)
        entries, order, remap = [], {}, []
        for index, (entry, raw) in enumerate(zip(layer.palette, layer.raw)):
            name = entry.get("name", "")
            if name.startswith(CUSTOM):
                if not used[index]:                 # 名字留在清單上、實際 0 格
                    raw = palette_entry("minecraft:air", {}, entry["version"])
                    cleared[name] += 1
                elif name not in blocks:
                    raise ConvertError(f"方塊 {name} 實際有 {used[index]} 格，對照表卻沒有登記")
                else:
                    rule = block_rule(blocks, name)
                    raw = palette_entry(rule["vanilla"], vanilla_state(rule, entry.get("states", {})), entry["version"])
                    counts[name] += used[index]
                    if rule.get("block_entity"):
                        for n, i in enumerate(indices):
                            if i == index:
                                x, z, y = cell_position(n)
                                frames.append(frame_entity(cx * 16 + x, sy * 16 + y, cz * 16 + z))
            if raw not in order:                    # 換完變成同一種的（門的通電狀態、空氣）合併成一項
                order[raw] = len(entries)
                entries.append(raw)
            remap.append(order[raw])
        layer.words = pack_indices([remap[i] for i in indices], layer.bits)
        layer.raw = entries
    return value[:subchunk_head_size(value)] + b"".join(write_layer(l) for l in layers), frames, counts, cleared


def _is_custom_item(item):
    name = item.get("Name")
    return name is not None and name[0] == 8 and name[1].startswith(CUSTOM)


def _empty_item(item):
    """物品欄的空格子長這樣（真實存檔裡玩家的終界箱欄位就是這樣）；保留格子編號。"""
    slot = {"Slot": item["Slot"]} if "Slot" in item else {}
    return {"Count": (1, 0), "Damage": (2, 0), "Name": (8, ""), **slot, "WasPickedUp": (1, 0)}


def remove_custom_items(node):
    """把一筆資料裡的自製物品拿掉，回傳拿掉幾個。箱子的 Items 直接少一筆，物品框架沒有
    Item 就是空的；其他地方（玩家物品欄、手上的東西）是固定的格子，換成空格子。"""
    tag, payload = node
    removed = 0
    if tag == 10:
        for key, (kind, value) in list(payload.items()):
            if kind == 10 and _is_custom_item(value):
                removed += 1
                if key == "Item":
                    del payload[key]
                else:
                    payload[key] = (10, _empty_item(value))
            elif kind == 9 and value[0] == 10:
                kept = []
                for item in value[1]:
                    if _is_custom_item(item):
                        removed += 1
                        if key != "Items":
                            kept.append(_empty_item(item))
                    else:
                        removed += remove_custom_items((10, item))
                        kept.append(item)
                payload[key] = (9, (10, kept))
            elif kind in (9, 10):
                removed += remove_custom_items((kind, value))
    elif tag == 9:
        for item in payload[1]:
            removed += remove_custom_items((payload[0], item))
    return removed


def filter_ticks(node):
    """拿掉提到自製方塊的待處理便條，回傳拿掉幾筆。"""
    kind, ticks = node[1]["tickList"][1]
    kept = [t for t in ticks if not t.get("blockState", (10, {}))[1].get("name", (8, ""))[1].startswith(CUSTOM)]
    node[1]["tickList"] = (9, (kind, kept))
    return len(ticks) - len(kept)


def drop_actor_ids(value, ids):
    """digp 記著每個區塊有哪些實體：每 8 位元組一個編號。"""
    return b"".join(value[i:i + 8] for i in range(0, len(value), 8) if value[i:i + 8] not in ids)


def _strip_or_stop(node, where):
    """拿掉物品之後，這筆資料不該再有任何自製識別碼。"""
    removed = remove_custom_items(node)
    data = write_typed("", node)
    if CUSTOM_BYTES in data:
        raise ConvertError(f"{where} 拿掉自製物品後還有自製識別碼，不知道該怎麼處理")
    return removed, data


def convert(db, blocks, entities):
    puts, deletes, add_entities, gone_actors = {}, [], defaultdict(list), set()
    stats = {"blocks": Counter(), "cleared": Counter(), "entities": Counter(), "items": 0, "ticks": 0}
    for key, value in db.iterate():
        if CUSTOM_BYTES not in value:
            continue
        where = parse_key(key)
        kind = where[0] if where else None
        if kind == "subchunk":
            puts[key], frames, counts, cleared = convert_subchunk(value, where, blocks)
            stats["blocks"].update(counts)
            stats["cleared"].update(cleared)
            if frames:
                add_entities[key[:-2] + b"\x31"].extend(frames)
        elif key.startswith(ACTOR):
            _, node, _ = read_typed(value)
            identifier = node[1].get("identifier", (8, ""))[1]
            item = node[1].get("Item", (0, {}))[1]
            if identifier.startswith(CUSTOM):
                if identifier not in entities:
                    raise ConvertError(f"實體 {identifier} 對照表沒有登記")
                stats["entities"][identifier] += 1
                gone_actors.add(key[len(ACTOR):])
                deletes.append(key)
            elif identifier == "minecraft:item" and _is_custom_item(item):   # 掉在地上的自製物品
                stats["items"] += 1
                gone_actors.add(key[len(ACTOR):])
                deletes.append(key)
            else:
                removed, puts[key] = _strip_or_stop(node, f"實體 {identifier}")
                stats["items"] += removed
        elif kind == "block_entity":
            out, pos = b"", 0
            while pos < len(value):
                _, node, pos = read_typed(value, pos)
                removed, data = _strip_or_stop(node, f"方塊實體 {node[1].get('id')}")
                stats["items"] += removed
                out += data
            puts[key] = out
        elif kind in ("pending_ticks", "random_ticks"):
            _, node, _ = read_typed(value)
            stats["ticks"] += filter_ticks(node)
            if node[1]["tickList"][1][1]:
                removed, puts[key] = _strip_or_stop(node, kind)
            else:
                deletes.append(key)
        elif key == b"~local_player" or key.startswith(b"player_"):
            _, node, _ = read_typed(value)
            removed, puts[key] = _strip_or_stop(node, "玩家")
            stats["items"] += removed
        else:
            raise ConvertError(f"{key!r} 裡有自製識別碼，不知道該怎麼處理")
    for key, extra in add_entities.items():
        base = puts.get(key)
        if base is None:
            try:
                base = db.get(key)
            except KeyError:
                base = b""
        puts[key] = base + b"".join(extra)
    if gone_actors:
        for key, value in db.iterate(b"digp", b"digq"):
            kept = drop_actor_ids(value, gone_actors)
            if kept != value:
                puts[key] = kept
    for key, value in puts.items():
        db.put(key, value)
    for key in deletes:
        db.delete(key)
    return stats


def blockers(report, blocks, entities):
    """預檢：列出會讓轉換停下來的東西。"""
    out = []
    for name, r in sorted(report["blocks"].items()):
        if r["cells"] and name not in blocks:
            sample = "、".join(f"{DIMS.get(p['dim'], p['dim'])} ({p['x']}, {p['y']}, {p['z']})" for p in r["positions"][:10])
            out.append(f"方塊 {name}：{r['cells']} 格沒有登記，例如 {sample}")
    for name, r in sorted(report["entities"].items()):
        if name not in entities:
            sample = "、".join(str([round(v, 1) for v in p]) for p in r["positions"][:10] if p)
            out.append(f"實體 {name}：{r['count']} 個沒有登記，例如 {sample}")
    for label, r in sorted(report["other"].items()):
        if label not in ("pending_ticks", "random_ticks"):
            out.append(f"{label} 裡有自製識別碼（{r['count']} 筆），不知道該怎麼處理")
    out += [f"解析錯誤 {e['kind']} {e['key']}：{e['error']}" for e in report["errors"][:10]]
    return out


def finish_world(folder, name):
    """世界改名、不啟用任何包。"""
    (folder / "levelname.txt").write_text(name, encoding="utf-8")
    for pack_list in ("world_resource_packs.json", "world_behavior_packs.json"):
        (folder / pack_list).write_text("[]\n", encoding="utf-8")
    (folder / "level.dat_old").unlink(missing_ok=True)
    raw = (folder / "level.dat").read_bytes()
    root_name, node, end = read_typed(raw, 8)
    if end != len(raw) or write_typed(root_name, node) != raw[8:]:
        raise ConvertError("level.dat 讀了再寫回去不完全相同，不敢改它")
    node[1]["LevelName"] = (8, name)
    body = write_typed(root_name, node)
    (folder / "level.dat").write_bytes(raw[:4] + struct.pack("<i", len(body)) + body)


def pack_world(folder, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(folder))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="把世界的副本轉成原味版 .mcworld，世界本體不動")
    parser.add_argument("world", help="世界的名稱或資料夾路徑")
    parser.add_argument("--mapping", default=str(REPO / "addon" / "mapping.json"), help="對照表（預設 addon/mapping.json）")
    parser.add_argument("--out", help="輸出的資料夾（預設 addon/build/worlds/）")
    args = parser.parse_args()

    world = find_world(args.world)
    source = world / "db"
    stop_if_game_uses(world)
    name = (world / "levelname.txt").read_text(encoding="utf-8", errors="replace").strip()
    print(f"世界：{name}（{world}）")
    need = sum(f.stat().st_size for f in source.iterdir())
    if shutil.disk_usage(tempfile.gettempdir()).free < need * 4:
        raise SystemExit(f"暫存資料夾所在的磁碟空間不夠，至少要 {need * 4 / 1e9:.1f} GB。")

    import leveldb                              # 放在這裡：環境沒裝好時，前面的檢查還是能跑

    blocks, entities = load_mapping(Path(args.mapping))
    before = snapshot(source)
    temp = Path(tempfile.mkdtemp(prefix="asuka_convert_"))
    try:
        copy = temp / "world"
        print(f"複製世界（{need / 1e9:.2f} GB）到暫存資料夾…")
        shutil.copytree(world, copy)

        print("預檢…")
        report = new_report()
        db = leveldb.LevelDB(str(copy / "db"), create_if_missing=False)
        try:
            report["seconds"] = 0
            scan(db, report)
            problems = blockers(report, blocks, entities)
            if problems:
                print("\n★轉換停止，沒有輸出任何檔案。請先處理：")
                for problem in problems:
                    print(f"  {problem}")
                sys.exit(2)
            print("轉換…")
            stats = convert(db, blocks, entities)
        finally:
            db.close()

        print("重新打開再掃一次…")
        after = new_report()
        db = leveldb.LevelDB(str(copy / "db"), create_if_missing=False)
        try:
            after["seconds"] = 0
            scan(db, after)
            left = sum(1 for k, v in db.iterate() if CUSTOM_BYTES in v)
        finally:
            db.close()
        if left or after["errors"]:
            show(after, blocks, entities)
            raise ConvertError(f"轉換後還有 {left} 筆資料提到自製識別碼，沒有輸出")

        finish_world(copy, f"{name} 原味版")
        out = Path(args.out or OUTPUT) / f"{name} 原味版.mcworld"
        print("打包…")
        pack_world(copy, out)
    except ConvertError as e:
        raise SystemExit(f"★轉換停止，沒有輸出任何檔案：{e}")
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    print("\n【換掉的自製方塊】" + ("" if stats["blocks"] else "（沒有）"))
    for block, cells in sorted(stats["blocks"].items()):
        print(f"  {block} {cells} 格 → {block_rule(blocks, block)['vanilla']}")
    print("【清掉的舊名字（實際 0 格）】" + ("" if stats["cleared"] else "（沒有）"))
    for block, entries in sorted(stats["cleared"].items()):
        print(f"  {block}：{entries} 項")
    print("【刪掉的自製實體】" + ("" if stats["entities"] else "（沒有）"))
    for entity, count in sorted(stats["entities"].items()):
        print(f"  {entity} {count} 個")
    print(f"【刪掉的自製物品】{stats['items']} 個")
    print(f"【刪掉的待處理便條】{stats['ticks']} 筆")
    same = snapshot(source) == before
    print(f"\n世界本體：{'檔案清單、大小與修改時間都沒變' if same else '★轉換前後不同，請檢查是不是遊戲或其他程式動過'}")
    print(f"輸出：{out}（{out.stat().st_size / 1e9:.2f} GB）")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
