"""convert.py 的小測試：不需要存檔，用造出來的資料驗證轉換是否正確。

執行：python tools/converter/test_convert.py
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert import (ConvertError, block_rule, convert_subchunk, drop_actor_ids, filter_ticks, palette_entry,
                     remove_custom_items, vanilla_state)
from test_world import layer
from world import cell_position, load_mapping, parse_subchunk, read_nbt, read_typed, write_typed

REPO = Path(__file__).resolve().parents[2]
BLOCKS, ENTITIES = load_mapping(REPO / "addon" / "mapping.json")
VERSION = 18168865
AIR = palette_entry("minecraft:air", {}, VERSION)
KEY = (("subchunk"), 0, 2, -1, 5)                # 區塊 (2, -1)、區段高度 5


def custom(name, states, version=VERSION):
    return palette_entry(name, states, version)


def names(layer_obj):
    return [e["name"] for e in layer_obj.palette]


def test_typed_round_trip():
    raw = custom("asukatech:door_white", {"asukatech:open": 1, "minecraft:cardinal_direction": "north"})
    name, value, end = read_typed(raw)
    assert end == len(raw) and write_typed(name, value) == raw


def test_entry_matches_the_game_exactly():
    # 從真實存檔查到的寫法：狀態照字母排序，_bit 是位元組，其他數字是整數，字串是字串
    raw = palette_entry("minecraft:spruce_door", {"upper_block_bit": 1, "open_bit": 0,
                                                  "minecraft:cardinal_direction": "south", "door_hinge_bit": 0}, VERSION)
    _, value, _ = read_typed(raw)
    states = value[1]["states"][1]
    assert list(states) == ["door_hinge_bit", "minecraft:cardinal_direction", "open_bit", "upper_block_bit"]
    assert states["open_bit"] == (1, 0) and states["minecraft:cardinal_direction"] == (8, "south")
    _, value, _ = read_typed(palette_entry("minecraft:sea_pickle", {"cluster_count": 1, "dead_bit": True}, VERSION))
    assert value[1]["states"][1] == {"cluster_count": (3, 1), "dead_bit": (1, 1)}
    assert value[1]["version"] == (3, VERSION)


def test_states_from_the_mapping():
    door = vanilla_state(block_rule(BLOCKS, "asukatech:door_white"), {"asukatech:upper": 1, "asukatech:open": 0, "asukatech:hinge_right": 1,
                                                                     "asukatech:powered": 1, "minecraft:cardinal_direction": "east"})
    assert door == {"upper_block_bit": 1, "open_bit": 0, "door_hinge_bit": 0, "minecraft:cardinal_direction": "south"}
    trapdoor = vanilla_state(block_rule(BLOCKS, "asukatech:trapdoor_light_gray"), {"asukatech:open": 1, "asukatech:powered": 0,
                                                                                   "minecraft:cardinal_direction": "south",
                                                                                   "minecraft:vertical_half": "top"})
    assert trapdoor == {"direction": 3, "upside_down_bit": True, "open_bit": 1}
    cup = vanilla_state(block_rule(BLOCKS, "asukatech:glass_cup"), {"asukatech:count": 3, "minecraft:cardinal_direction": "west"})
    assert cup == {"cluster_count": 2, "dead_bit": True}
    frame = vanilla_state(block_rule(BLOCKS, "asukatech:screen"), {"minecraft:block_face": "east"})
    assert frame == {"facing_direction": 5, "item_frame_map_bit": False, "item_frame_photo_bit": False}


def test_same_as_the_authors_side_by_side_test():
    # 作者在遊戲裡並排放原版與自製的門、地板門對照（2026-11-04），這些數值都是從那次的存檔讀的。
    # 玩家面向北：原版門存 east、白色門存 north；面向東：原版門存 south、白色門存 east。
    # 白色門預設的門軸在玩家右手邊（hinge_right 0），也就是原版的 door_hinge_bit 1。
    def door(direction, upper):
        return vanilla_state(block_rule(BLOCKS, "asukatech:door_white"), {
            "asukatech:upper": upper, "asukatech:open": 1, "asukatech:hinge_right": 0, "asukatech:powered": 0,
            "minecraft:cardinal_direction": direction})
    assert door("north", 0) == {"door_hinge_bit": 0, "minecraft:cardinal_direction": "east", "open_bit": 1, "upper_block_bit": 0}
    assert door("north", 1) == {"door_hinge_bit": 1, "minecraft:cardinal_direction": "east", "open_bit": 0, "upper_block_bit": 1}
    assert door("east", 0)["minecraft:cardinal_direction"] == "south"
    assert door("south", 0)["minecraft:cardinal_direction"] == "west"
    assert door("west", 0)["minecraft:cardinal_direction"] == "north"

    def trapdoor(direction):
        return vanilla_state(block_rule(BLOCKS, "asukatech:trapdoor_white"), {
            "asukatech:open": 1, "asukatech:powered": 0, "minecraft:cardinal_direction": direction,
            "minecraft:vertical_half": "bottom"})["direction"]
    assert [trapdoor(d) for d in ("north", "east", "south", "west")] == [2, 1, 3, 0]


def test_subchunk_door_and_cup():
    door = custom("asukatech:door_white", {"asukatech:upper": 0, "asukatech:open": 1, "asukatech:hinge_right": 0,
                                           "asukatech:powered": 0, "minecraft:cardinal_direction": "north"})
    door_powered = custom("asukatech:door_white", {"asukatech:upper": 0, "asukatech:open": 1, "asukatech:hinge_right": 0,
                                                   "asukatech:powered": 1, "minecraft:cardinal_direction": "north"})
    cup = custom("asukatech:coffee_cup", {"asukatech:count": 1, "minecraft:cardinal_direction": "north"})
    stone = palette_entry("minecraft:stone", {}, VERSION)
    indices = [0] * 4096
    indices[1] = 1       # 門
    indices[2] = 2       # 通電的門：原版沒有這個狀態，會和上一種變成同一項，要合併
    indices[3] = 3       # 咖啡杯：變成空氣，和第 0 項合併
    indices[4] = 4       # 石頭：不能被動到
    data = bytes([9, 1, 5]) + layer(indices, 3, [AIR, door, door_powered, cup, stone])
    new, frames, counts, cleared = convert_subchunk(data, KEY, BLOCKS)
    assert new[:3] == bytes([9, 1, 5])           # 開頭原封不動
    result = parse_subchunk(new)[0]
    assert names(result) == ["minecraft:air", "minecraft:spruce_door", "minecraft:stone"]
    got = list(result.indices())
    assert got[1] == got[2] == 1 and got[3] == 0 and got[4] == 2 and got[0] == 0 and sum(got) == 1 + 1 + 2
    assert result.palette[1]["states"] == {"door_hinge_bit": 0, "minecraft:cardinal_direction": "east", "open_bit": 1, "upper_block_bit": 0}
    assert counts == {"asukatech:door_white": 2, "asukatech:coffee_cup": 1} and not frames and not cleared


def test_unused_names_are_cleared_even_if_not_registered():
    # 舊履帶：名字留在清單上、實際 0 格。換成空氣，不報錯（2026-11-04）
    data = bytes([8, 1]) + layer([0] * 4096, 1, [AIR, custom("asukatech:conveyor", {"asukatech:shape": 0})])
    new, _, counts, cleared = convert_subchunk(data, KEY, BLOCKS)
    assert names(parse_subchunk(new)[0]) == ["minecraft:air"]
    assert not counts and cleared == {"asukatech:conveyor": 1}


def test_used_but_not_registered_stops():
    indices = [0] * 4096
    indices[7] = 1
    data = bytes([8, 1]) + layer(indices, 1, [AIR, custom("asukatech:conveyor", {"asukatech:shape": 0})])
    try:
        convert_subchunk(data, KEY, BLOCKS)
    except ConvertError:
        return
    raise AssertionError("真的有方塊又沒登記，一定要停下來")


def test_screen_gets_its_block_entity_at_the_right_place():
    indices = [0] * 4096
    n = (3 << 8) | (4 << 4) | 6                  # x 3、z 4、y 6
    indices[n] = 1
    assert cell_position(n) == (3, 4, 6)
    data = bytes([8, 1]) + layer(indices, 1, [AIR, custom("asukatech:screen", {"minecraft:block_face": "north"})])
    new, frames, counts, _ = convert_subchunk(data, KEY, BLOCKS)
    frame = read_nbt(frames[0])[1]
    assert frame == {"BlockEntityVersion": 0, "id": "GlowItemFrame", "x": 2 * 16 + 3, "y": 5 * 16 + 6, "z": -16 + 4}
    assert parse_subchunk(new)[0].palette[1]["states"]["facing_direction"] == 2


def typed(value):
    """把 Python 的資料變成 read_typed 的樣子，寫測試比較短。"""
    if isinstance(value, dict):
        return (10, {k: typed(v) for k, v in value.items()})
    if isinstance(value, str):
        return (8, value)
    if isinstance(value, list):
        return (9, (10, [typed(v)[1] for v in value]))
    return (1, value)


def test_remove_items_from_a_chest():
    chest = typed({"id": "Chest", "Items": [{"Name": "asukatech:plate", "Count": 3, "Slot": 0},
                                            {"Name": "minecraft:stone", "Count": 1, "Slot": 1}]})
    assert remove_custom_items(chest) == 1
    items = chest[1]["Items"][1][1]
    assert len(items) == 1 and items[0]["Name"] == (8, "minecraft:stone")


def test_remove_items_from_a_player_keeps_slots():
    player = typed({"Inventory": [{"Name": "asukatech:ipad", "Count": 1, "Slot": 4, "Block": {"name": "asukatech:ipad"}}],
                    "Mainhand": [{"Name": "asukatech:plate", "Count": 1}]})
    assert remove_custom_items(player) == 2
    slot = player[1]["Inventory"][1][1][0]
    assert slot["Name"] == (8, "") and slot["Count"] == (1, 0) and slot["Slot"] == (1, 4) and "Block" not in slot
    assert player[1]["Mainhand"][1][1][0]["Name"] == (8, "")


def test_remove_items_inside_a_shulker_and_a_frame():
    box = typed({"id": "ShulkerBox", "Items": [{"Name": "minecraft:white_shulker_box", "Slot": 0,
                                                "tag": {"Items": [{"Name": "asukatech:cup", "Slot": 2}]}}]})
    assert remove_custom_items(box) == 1
    assert box[1]["Items"][1][1][0]["tag"][1]["Items"][1][1] == []
    frame = typed({"id": "ItemFrame", "Item": {"Name": "asukatech:plate", "Count": 1}})
    assert remove_custom_items(frame) == 1 and "Item" not in frame[1]


def test_ticks():
    ticks = typed({"tickList": [{"blockState": {"name": "asukatech:door_white"}}, {"blockState": {"name": "minecraft:water"}}]})
    assert filter_ticks(ticks) == 1
    assert [t["blockState"][1]["name"][1] for t in ticks[1]["tickList"][1][1]] == ["minecraft:water"]


def test_drop_actor_ids():
    a, b, c = b"A" * 8, b"B" * 8, b"C" * 8
    assert drop_actor_ids(a + b + c, {b}) == a + c
    assert drop_actor_ids(a + c, {b}) == a + c
    assert drop_actor_ids(b, {b}) == b""


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print("通過", test.__name__)
    print(f"全部 {len(tests)} 項通過")
