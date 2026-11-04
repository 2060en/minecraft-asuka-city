"""world.py 的小測試：不需要存檔，用造出來的資料驗證解析是否正確。

執行：python tools/converter/test_world.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from world import cell_position, load_mapping, parse_key, parse_subchunk, read_nbt, read_all_nbt, walk_custom

REPO = Path(__file__).resolve().parents[2]


def s(text):
    """NBT 的字串：2 位元組長度＋內容。"""
    b = text.encode()
    return struct.pack("<H", len(b)) + b


def entry(name, states=b""):
    """造一個調色盤項目 {name, states, version}。"""
    return (b"\x0a" + s("") + b"\x08" + s("name") + s(name) + b"\x0a" + s("states") + states + b"\x00"
            + b"\x03" + s("version") + struct.pack("<i", 18000000) + b"\x00")


def layer(indices, bits, palette):
    """造一層：每個 32 位元的字裝 32 // bits 格，低位元在前。"""
    head = bytes([bits << 1])
    size = struct.pack("<i", len(palette))
    if bits == 0:
        return head + size + b"".join(palette)
    per = 32 // bits
    words = []
    for i in range(0, 4096, per):
        word = 0
        for j, index in enumerate(indices[i:i + per]):
            word |= index << (j * bits)
        words.append(word)
    return head + struct.pack(f"<{len(words)}I", *words) + size + b"".join(palette)


def test_nbt():
    states = b"\x01" + s("open_bit") + b"\x01" + b"\x03" + s("direction") + struct.pack("<i", 2) \
        + b"\x08" + s("minecraft:cardinal_direction") + s("north")
    name, value, end = read_nbt(entry("asukatech:door_white", states))
    assert name == ""
    assert value["name"] == "asukatech:door_white"
    assert value["states"] == {"open_bit": 1, "direction": 2, "minecraft:cardinal_direction": "north"}
    assert value["version"] == 18000000
    assert end == len(entry("asukatech:door_white", states))


def test_consecutive_roots():
    assert [v["name"] for v in read_all_nbt(entry("a") + entry("b"))] == ["a", "b"]


def test_subchunk_two_layers():
    indices = [0] * 4096
    indices[5] = 1
    indices[4095] = 1
    data = bytes([9, 2, 0xFE]) + layer(indices, 1, [entry("minecraft:air"), entry("asukatech:door_white")]) \
        + layer([0] * 4096, 0, [entry("minecraft:water")])
    layers = parse_subchunk(data)
    assert len(layers) == 2
    got = list(layers[0].indices())
    assert len(got) == 4096 and got == indices
    assert [p["name"] for p in layers[0].palette] == ["minecraft:air", "asukatech:door_white"]
    assert list(layers[1].indices()) == [0] * 4096
    assert layers[1].palette[0]["name"] == "minecraft:water"


def test_subchunk_words_with_spare_bits():
    # 3 位元：每個字裝 10 格，剩 2 位元不用；要跨字邊界也算對
    indices = [n % 5 for n in range(4096)]
    data = bytes([8, 1]) + layer(indices, 3, [entry(f"block_{n}") for n in range(5)])
    assert list(parse_subchunk(data)[0].indices()) == indices


def test_subchunk_trailing_bytes_are_an_error():
    data = bytes([8, 1]) + layer([0] * 4096, 0, [entry("minecraft:air")]) + b"\x00"
    try:
        parse_subchunk(data)
    except ValueError:
        return
    raise AssertionError("多餘的資料應該要報錯，不能當作讀對了")


def test_cell_position():
    # 順序是 x、z、y：y 跑最快
    assert cell_position(0) == (0, 0, 0)
    assert cell_position(1) == (0, 0, 1)
    assert cell_position(16) == (0, 1, 0)
    assert cell_position(256) == (1, 0, 0)
    assert cell_position(4095) == (15, 15, 15)


def test_keys():
    overworld = struct.pack("<ii", 3, -2) + bytes([0x2f]) + struct.pack("<b", -4)
    assert parse_key(overworld) == ("subchunk", 0, 3, -2, -4)
    nether = struct.pack("<iii", 1, 2, 1) + bytes([0x2f, 5])
    assert parse_key(nether) == ("subchunk", 1, 1, 2, 5)
    assert parse_key(struct.pack("<ii", 3, -2) + bytes([0x31])) == ("block_entity", 0, 3, -2, None)
    assert parse_key(b"~local_player") is None
    assert parse_key(b"actorprefix12345678") is None


def test_walk_custom():
    value = {"Name": "asukatech:plate", "Items": [{"Name": "minecraft:stone"}, {"Name": "asukatech:ipad"}], "n": 3}
    assert sorted(walk_custom(value)) == ["asukatech:ipad", "asukatech:plate"]


def test_mapping():
    blocks, entities = load_mapping(REPO / "addon" / "mapping.json")
    assert "asukatech:door_white" in blocks and "asukatech:glass_cup" in blocks
    assert not any(k.startswith("_") for k in blocks)
    assert "asukatech:ipad" in entities and "asukatech:luggage_cart_pink" in entities
    assert len(blocks) == 7 and len(entities) == 18    # docs/addon-contents.md：7 種方塊、18 種實體


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print("通過", test.__name__)
    print(f"全部 {len(tests)} 項通過")
