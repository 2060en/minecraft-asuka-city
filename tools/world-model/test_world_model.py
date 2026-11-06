"""區域 3D 模型的小測試：不需要存檔，也不需要下載原版材質，用造出來的資料驗證讀取與形狀。

執行：tools/world-model/.venv/Scripts/python.exe tools/world-model/test_world_model.py
"""
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "converter"))
from test_world import entry, layer, s  # noqa: E402  轉換程式測試裡造 NBT 與區段的小工具

import build  # noqa: E402
from extract import read_box  # noqa: E402


class FakeDB:
    """和 amulet-leveldb 一樣：找不到的鍵丟 KeyError。"""
    def __init__(self, data):
        self.data = data

    def get(self, key):
        return self.data[key]


def compound(*fields):
    return b"\x0a" + s("") + b"".join(fields) + b"\x00"


def int_field(name, value):
    return b"\x03" + s(name) + struct.pack("<i", value)


def str_field(name, value):
    return b"\x08" + s(name) + s(value)


def test_read_box():
    # 區塊 (0, 0) 的第 4 段（y 64～79）：(1, 67, 2) 放石頭、(3, 64, 0) 放玻璃
    indices = [0] * 4096
    indices[(1 << 8) | (2 << 4) | 3] = 1
    indices[(3 << 8) | (0 << 4) | 0] = 2
    sub = bytes([8, 1]) + layer(indices, 2, [entry("minecraft:air"), entry("minecraft:stone"), entry("minecraft:glass")])
    sign = compound(str_field("id", "Sign"), int_field("x", 1), int_field("y", 67), int_field("z", 2))
    far = compound(str_field("id", "Sign"), int_field("x", 9), int_field("y", 67), int_field("z", 2))
    pos = b"\x09" + s("Pos") + b"\x05" + struct.pack("<i", 3) + struct.pack("<fff", 1.5, 65.0, 0.5)
    actor = compound(str_field("identifier", "minecraft:npc"), pos)
    db = FakeDB({
        struct.pack("<iiBb", 0, 0, 0x2F, 4): sub,
        struct.pack("<iiB", 0, 0, 0x31): sign + far,
        b"digp" + struct.pack("<ii", 0, 0): b"\x01" * 8,
        b"actorprefix" + b"\x01" * 8: actor,
    })
    grid, palette, block_entities, entities, missing = read_box(db, [0, 3, 64, 70, 0, 3])
    names = [p["name"] for p in palette]
    assert grid.shape == (7, 4, 4)                     # [y][z][x]
    assert names[grid[67 - 64, 2, 1]] == "minecraft:stone"
    assert names[grid[0, 0, 3]] == "minecraft:glass"
    assert sum(1 for v in grid.flat if v) == 2
    assert [(e["x"], e["y"], e["z"]) for e in block_entities] == [(1, 67, 2)]   # 範圍外的告示牌不要
    assert [e["identifier"] for e in entities] == ["minecraft:npc"]
    assert missing == 0


def test_missing_subchunk_is_air():
    grid, palette, *_ = read_box(FakeDB({}), [0, 15, 0, 15, 0, 15])
    assert not grid.any() and palette[0]["name"] == "minecraft:air"


def shape(name, states=None):
    """不讀材質（形狀不需要），找不到的材質會標成 unknown。"""
    return build.spec_for("minecraft:" + name, states or {})


def test_shapes():
    assert shape("air")["k"] == "none" and shape("light_block_15")["k"] == "none"
    assert shape("stone")["k"] == "cube"
    assert shape("smooth_quartz_slab", {"minecraft:vertical_half": "bottom"})["b"] == [[0, 0, 0, 16, 8, 16]]
    assert shape("smooth_quartz_slab", {"minecraft:vertical_half": "top"})["b"] == [[0, 8, 0, 16, 16, 16]]
    assert shape("white_concrete_double_slab")["k"] == "cube"
    stairs = shape("quartz_stairs", {"weirdo_direction": 0, "upside_down_bit": 0})["b"]
    assert stairs == [[0, 0, 0, 16, 8, 16], [8, 8, 0, 16, 16, 16]]   # 0 朝東：高的那半在東邊
    assert shape("gray_carpet")["b"] == [[0, 0, 0, 16, 1, 16]]
    pane = shape("white_stained_glass_pane")
    assert pane["k"] == "pane" and pane["g"] == 1 and pane["m"] == 2
    assert shape("glass")["m"] == 1 and shape("glass")["g"] == 1      # 透明玻璃用鏤空，染色玻璃半透明
    assert shape("oak_fence")["k"] == "fence"
    wall = shape("andesite_wall", {"wall_post_bit": 0, "wall_connection_type_east": "short", "wall_connection_type_north": "none",
                                   "wall_connection_type_south": "none", "wall_connection_type_west": "tall"})
    assert wall["b"] == [[8, 0, 5, 16, 14, 11], [0, 0, 5, 8, 16, 11]]   # 東邊矮、西邊高，沒有中間的柱子
    sign = shape("darkoak_wall_sign", {"facing_direction": 3})          # 3 朝南：板子貼在北邊的牆上
    assert sign["sign"] == ["wall", "south"] and sign["b"][0][2] == 0 and sign["b"][0][5] == 2


def test_banner_colors():
    # 基岩版旗幟的舊染料編號：0 黑、3 棕、15 白
    assert build.DYE[build.BANNER_TO_DYE[0]] == build.DYE[15]
    assert build.DYE[build.BANNER_TO_DYE[3]] == build.DYE[12]
    assert build.DYE[build.BANNER_TO_DYE[15]] == build.DYE[0]


def test_three_bundle():
    if not build.THREE.exists():
        print("  （略過：tools/preview 還沒 npm install）")
        return
    code = build.three_classic()
    assert code.startswith("(function(){") and "window.THREE=" in code and "</script" not in code.lower()


def test_viewer_syntax():
    if not shutil.which("node"):
        print("  （略過：沒有 node）")
        return
    subprocess.run(["node", "--check", str(HERE / "viewer.js")], check=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print("通過", test.__name__)
    print(f"全部 {len(tests)} 項通過")
