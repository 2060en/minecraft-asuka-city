"""讀基岩版存檔的共用程式：NBT、區段（調色盤＋索引）、資料庫的鍵、對照表。

存檔是 Mojang 版的 LevelDB，裡面的數字都是小端序。這裡只處理掃描與轉換用得到的
部分；看不懂的資料一律報錯，不猜。
"""
import json
import math
import struct
from dataclasses import dataclass

CUSTOM = "asukatech:"
CUSTOM_BYTES = CUSTOM.encode()

# 區塊資料的鍵：區塊 x、z（各 4 位元組），主世界以外再多 4 位元組的維度，然後是一個種類碼
KEY_KINDS = {0x2f: "subchunk", 0x31: "block_entity", 0x32: "entity_old", 0x33: "pending_ticks", 0x3a: "random_ticks"}

_SIMPLE = {1: ("<b", 1), 2: ("<h", 2), 3: ("<i", 4), 4: ("<q", 8), 5: ("<f", 4), 6: ("<d", 8)}


def _read_string(buf, pos):
    size = struct.unpack_from("<H", buf, pos)[0]
    pos += 2
    return buf[pos:pos + size].decode("utf-8", errors="replace"), pos + size


def _read_payload(buf, pos, tag):
    if tag in _SIMPLE:
        fmt, size = _SIMPLE[tag]
        return struct.unpack_from(fmt, buf, pos)[0], pos + size
    if tag == 8:
        return _read_string(buf, pos)
    if tag == 9:                                # 串列：元素種類＋個數
        kind, count = struct.unpack_from("<bi", buf, pos)
        pos += 5
        items = []
        for _ in range(count):
            item, pos = _read_payload(buf, pos, kind)
            items.append(item)
        return items, pos
    if tag == 10:                               # 複合：一筆一筆讀到種類 0 為止
        value = {}
        while True:
            kind = buf[pos]
            pos += 1
            if kind == 0:
                return value, pos
            name, pos = _read_string(buf, pos)
            value[name], pos = _read_payload(buf, pos, kind)
    if tag in (7, 11, 12):                      # 陣列：個數＋內容
        count = struct.unpack_from("<i", buf, pos)[0]
        fmt, size = {7: ("b", 1), 11: ("i", 4), 12: ("q", 8)}[tag]
        return list(struct.unpack_from(f"<{count}{fmt}", buf, pos + 4)), pos + 4 + count * size
    raise ValueError(f"不認得的 NBT 種類 {tag}（位置 {pos}）")


def read_nbt(buf, pos=0):
    """讀一個根節點，回傳 (名稱, 值, 下一個位置)。"""
    tag = buf[pos]
    name, pos = _read_string(buf, pos + 1)
    value, pos = _read_payload(buf, pos, tag)
    return name, value, pos


def read_all_nbt(buf):
    """方塊實體這類資料是好幾個根節點接在一起。"""
    values, pos = [], 0
    while pos < len(buf):
        _, value, pos = read_nbt(buf, pos)
        values.append(value)
    return values


def walk_custom(value):
    """把一筆 NBT 裡所有自製識別碼的字串找出來（物品名稱等）。"""
    if isinstance(value, str):
        if value.startswith(CUSTOM):
            yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_custom(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_custom(item)


@dataclass
class Layer:
    """區段的一層（第二層通常是含水方塊的水）。"""
    palette: list
    words: tuple
    bits: int

    def indices(self):
        """依序產生 4096 格各自的調色盤編號；每個字從低位元開始裝。"""
        if self.bits == 0:                      # 整層同一種方塊，不存索引
            yield from (0 for _ in range(4096))
            return
        per_word, mask, done = 32 // self.bits, (1 << self.bits) - 1, 0
        for word in self.words:
            for _ in range(per_word):
                if done == 4096:
                    return
                yield word & mask
                word >>= self.bits
                done += 1


def parse_subchunk(data):
    """把一個區段的值解開成好幾層；有多餘或不足的資料就報錯。"""
    version, pos = data[0], 1
    if version == 1:
        count = 1
    elif version in (8, 9):
        count = data[pos]
        pos += 2 if version == 9 else 1         # 第 9 版多一個位元組記自己的高度
    else:
        raise ValueError(f"不認得的區段版本 {version}")
    layers = []
    for _ in range(count):
        bits = data[pos] >> 1
        pos += 1
        words = ()
        if bits:
            if bits > 32:
                raise ValueError(f"不合理的索引位元數 {bits}")
            total = math.ceil(4096 / (32 // bits))
            words = struct.unpack_from(f"<{total}I", data, pos)
            pos += 4 * total
        size = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        palette = []
        for _ in range(size):
            _, entry, pos = read_nbt(data, pos)
            palette.append(entry)
        layers.append(Layer(palette, words, bits))
    if pos != len(data):
        raise ValueError(f"區段讀完還剩 {len(data) - pos} 位元組")
    return layers


def cell_position(n):
    """第 n 格在區段裡的位置 (x, z, y)：y 跑最快，然後 z，最後 x。"""
    return n >> 8, (n >> 4) & 15, n & 15


def parse_key(key):
    """區塊資料的鍵回傳 (種類, 維度, 區塊 x, 區塊 z, 區段 y)，其他的回傳 None。"""
    if len(key) in (9, 10):
        dim, at = 0, 8
    elif len(key) in (13, 14):
        dim, at = struct.unpack_from("<i", key, 8)[0], 12
    else:
        return None
    kind = KEY_KINDS.get(key[at])
    if kind is None or (len(key) - at == 2) != (kind == "subchunk"):
        return None
    x, z = struct.unpack_from("<ii", key)
    y = struct.unpack_from("<b", key, at + 1)[0] if kind == "subchunk" else None
    return kind, dim, x, z, y


def load_mapping(path):
    """讀 addon/mapping.json，回傳 (登記的方塊, 登記要刪的實體)。底線開頭的是說明。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    blocks = {k: v for k, v in data.items() if not k.startswith("_")}
    return blocks, set(data["_實體"]["delete"])
