"""只讀不寫：把世界裡一個長方體範圍的方塊、方塊實體（告示牌、旗幟…）與實體（NPC、畫、盔甲座…）讀出來，
給 build.py 做 3D 模型、給 plans.py 做平面圖。

用法（第一次先照 README 裝好環境）：

    tools/world-model/.venv/Scripts/python.exe tools/world-model/extract.py CX198-test --preset akq --out <資料夾>
    tools/world-model/.venv/Scripts/python.exe tools/world-model/extract.py CX198 --box 686 840 62 95 205 500 --out <資料夾>

世界可以給名稱（levelname.txt，要完全相同）或世界資料夾的路徑。和轉換程式的掃描（scan.py）用同一套保護：
世界本體絕對不開，先把 db 複製到暫存資料夾，只開那份副本，結束就刪掉；遊戲開著時拒絕讀遊戲資料夾裡的世界；
結束前核對世界本體的檔案清單、大小與修改時間，確認完全沒變。
"""
import argparse
import json
import shutil
import struct
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "converter"))
from scan import find_world, snapshot, stop_if_game_uses  # noqa: E402
from world import parse_subchunk, read_all_nbt, read_nbt  # noqa: E402

SUBCHUNK, BLOCK_ENTITY = 0x2F, 0x31


def jsonable(v):
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    if isinstance(v, bytes):
        return v.hex()
    return v


def get(db, key):
    try:
        return db.get(key)
    except KeyError:                            # amulet-leveldb 找不到時丟 KeyError
        return None


def read_box(db, box):
    """讀一個長方體範圍（只限主世界），回傳 (方塊編號陣列 [y][z][x], 調色盤, 方塊實體, 實體, 缺少的區段數)。"""
    x0, x1, y0, y1, z0, z1 = box
    grid = np.zeros((y1 - y0 + 1, z1 - z0 + 1, x1 - x0 + 1), dtype=np.uint16)   # 0 = 空氣（或沒有資料）
    palette = [{"name": "minecraft:air", "states": {}}]
    index = {json.dumps(palette[0], sort_keys=True): 0}
    missing = 0
    block_entities, entities = [], []

    for cx in range(x0 >> 4, (x1 >> 4) + 1):
        for cz in range(z0 >> 4, (z1 >> 4) + 1):
            for cy in range(y0 >> 4, (y1 >> 4) + 1):
                data = get(db, struct.pack("<iiBb", cx, cz, SUBCHUNK, cy))
                if data is None:                # 整段都是空氣時遊戲不存
                    missing += 1
                    continue
                layer = parse_subchunk(data)[0]  # 第二層通常是含水方塊的水，模型不畫
                local = []
                for e in layer.palette:
                    entry = {"name": e.get("name"), "states": e.get("states", {})}
                    key = json.dumps(entry, sort_keys=True)
                    if key not in index:
                        index[key] = len(palette)
                        palette.append(entry)
                    local.append(index[key])
                cells = np.fromiter(layer.indices(), dtype=np.int32, count=4096)
                vals = np.array(local, dtype=np.uint16)[cells].reshape(16, 16, 16)   # 第 n 格：x = n>>8、z = (n>>4)&15、y = n&15
                bx, bz, by = cx * 16, cz * 16, cy * 16
                xa, xb = max(x0, bx), min(x1, bx + 15)
                za, zb = max(z0, bz), min(z1, bz + 15)
                ya, yb = max(y0, by), min(y1, by + 15)
                part = vals[xa - bx:xb - bx + 1, za - bz:zb - bz + 1, ya - by:yb - by + 1]
                grid[ya - y0:yb - y0 + 1, za - z0:zb - z0 + 1, xa - x0:xb - x0 + 1] = part.transpose(2, 1, 0)

            raw = get(db, struct.pack("<iiB", cx, cz, BLOCK_ENTITY))
            for e in read_all_nbt(raw) if raw else []:
                if x0 <= e.get("x", x0 - 1) <= x1 and y0 <= e.get("y", y0 - 1) <= y1 and z0 <= e.get("z", z0 - 1) <= z1:
                    block_entities.append(jsonable(e))

            ids = get(db, b"digp" + struct.pack("<ii", cx, cz))   # 這個區塊的實體編號清單，每個 8 位元組
            for i in range(0, len(ids or b""), 8):
                raw = get(db, b"actorprefix" + ids[i:i + 8])
                if raw:
                    actor = read_nbt(raw)[1]
                    px, py, pz = actor.get("Pos") or [0, 0, 0]
                    if x0 <= px <= x1 + 1 and y0 <= py <= y1 + 1 and z0 <= pz <= z1 + 1:
                        entities.append(jsonable(actor))
    return grid, palette, block_entities, entities, missing


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="只讀世界的副本，把一個範圍的方塊與實體讀出來")
    parser.add_argument("world", help="世界的名稱或資料夾路徑")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preset", help="範圍設定的名稱（presets/<名稱>.json）或 .json 路徑")
    group.add_argument("--box", nargs=6, type=int, metavar=("X0", "X1", "Y0", "Y1", "Z0", "Z1"), help="直接給範圍")
    parser.add_argument("--out", required=True, help="輸出資料夾（建議放在 repo 外面）")
    args = parser.parse_args()

    if args.preset:
        path = Path(args.preset) if args.preset.endswith(".json") else HERE / "presets" / f"{args.preset}.json"
        box = json.loads(path.read_text(encoding="utf-8"))["box"]
    else:
        box = args.box
    x0, x1, y0, y1, z0, z1 = box
    if x0 > x1 or y0 > y1 or z0 > z1:
        raise SystemExit("範圍的起點要小於終點：X0 X1 Y0 Y1 Z0 Z1")

    world = find_world(args.world)
    source = world / "db"
    stop_if_game_uses(world)
    name = (world / "levelname.txt").read_text(encoding="utf-8", errors="replace").strip()
    saved = datetime.fromtimestamp(max(f.stat().st_mtime for f in source.iterdir())).strftime("%Y-%m-%d %H:%M")
    print(f"世界：{name}（{world}），最後存檔 {saved}")
    packs = []
    if (world / "world_resource_packs.json").exists():
        packs = [p.get("pack_id") for p in json.loads((world / "world_resource_packs.json").read_text(encoding="utf-8"))]

    import leveldb                              # 放在這裡：環境沒裝好時，前面的檢查還是能跑

    before = snapshot(source)
    temp = Path(tempfile.mkdtemp(prefix="asuka_model_"))
    try:
        need = sum(f.stat().st_size for f in source.iterdir())
        if shutil.disk_usage(temp).free < need * 2:
            raise SystemExit(f"暫存資料夾所在的磁碟空間不夠，至少要 {need * 2 / 1e9:.1f} GB。")
        print(f"複製 db（{need / 1e9:.2f} GB）到暫存資料夾…")
        shutil.copytree(source, temp / "db")
        db = leveldb.LevelDB(str(temp / "db"), create_if_missing=False)
        try:
            grid, palette, block_entities, entities, missing = read_box(db, box)
        finally:
            db.close()
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    same = snapshot(source) == before

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "region.npz", grid=grid)
    meta = {"world": name, "folder": world.name, "saved": saved, "resource_packs": packs,
            "origin": [x0, y0, z0], "size": [x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1], "palette": palette, "missing_subchunks": missing}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (out / "block_entities.json").write_text(json.dumps(block_entities, ensure_ascii=False), encoding="utf-8")
    (out / "entities.json").write_text(json.dumps(entities, ensure_ascii=False), encoding="utf-8")
    print(f"範圍 {meta['size'][0]}×{meta['size'][1]}×{meta['size'][2]}（X×Y×Z），方塊種類 {len(palette)}，"
          f"方塊實體 {len(block_entities)}，實體 {len(entities)}，全是空氣的區段 {missing}")
    print(f"世界本體：{'檔案清單、大小與修改時間都沒變' if same else '★讀取前後不同，請檢查是不是遊戲或其他程式動過'}")
    print(f"輸出：{out}")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
