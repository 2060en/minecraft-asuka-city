"""把 extract.py 讀出的方塊資料做成可以在瀏覽器旋轉、縮放的 3D 模型（單一 HTML 檔，雙擊就能開）。

用法（環境照 README 裝好）：

    tools/world-model/.venv/Scripts/python.exe tools/world-model/build.py <資料夾> --preset akq --out <網頁.html>

材質：Mojang 官方 bedrock-samples 的原版資源包（第一次用時自動下載到 .cache/，不進 repo），
再疊上世界掛的 Asuka tech 資源包（依照資源包編號到 addon/build/ 裡找，所以要先組過包）。
"""
import argparse
import base64
import io
import json
import re
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SAMPLES = HERE / ".cache" / "bedrock-samples"
BS = SAMPLES / "resource_pack"
THREE = REPO / "tools" / "preview" / "node_modules" / "three" / "build"
DEVRP = None            # 世界掛的資源包資料夾，load_packs() 設定；沒有時只用原版
BLOCKS, TERRAIN = {}, {}
# 只下載用得到的部分：方塊材質、畫、旗幟圖樣與兩張對照表
SPARSE = ["/resource_pack/blocks.json", "/resource_pack/textures/terrain_texture.json", "/resource_pack/textures/blocks/",
          "/resource_pack/textures/painting/", "/resource_pack/textures/entity/banner/"]


def load_json(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    return json.loads(text)


def ensure_samples():
    """原版材質還沒下載時，用 git 只抓需要的資料夾（約 15 MB）。"""
    if (BS / "blocks.json").exists():
        return
    print("第一次使用：從 GitHub 下載 Mojang 官方原版資源包的材質（約 15 MB）…")
    SAMPLES.parent.mkdir(parents=True, exist_ok=True)
    git = ["git", "-C", str(SAMPLES)]
    subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                    "https://github.com/Mojang/bedrock-samples.git", str(SAMPLES)], check=True)
    subprocess.run(git + ["sparse-checkout", "init", "--no-cone"], check=True)
    (SAMPLES / ".git" / "info" / "sparse-checkout").write_text("\n".join(SPARSE) + "\n", encoding="utf-8")
    subprocess.run(git + ["checkout", "-q"], check=True)


def find_pack(pack_ids):
    """世界掛的資源包編號 → addon/build/ 裡組好的資源包資料夾；找不到回傳 None。"""
    for manifest in sorted((REPO / "addon" / "build").glob("**/manifest.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("header", {}).get("uuid") in pack_ids and any(m.get("type") == "resources" for m in data.get("modules", [])):
            return manifest.parent
    return None


def load_packs(pack):
    """讀原版的方塊與材質對照表，再疊上資源包的。"""
    global DEVRP, BLOCKS, TERRAIN
    DEVRP = pack
    BLOCKS = load_json(BS / "blocks.json")
    TERRAIN = load_json(BS / "textures" / "terrain_texture.json")["texture_data"]
    if pack and (pack / "blocks.json").exists():
        BLOCKS.update({k.split(":")[-1] if k.startswith("minecraft:") else k: v for k, v in load_json(pack / "blocks.json").items()})
    if pack and (pack / "textures" / "terrain_texture.json").exists():
        TERRAIN.update(load_json(pack / "textures" / "terrain_texture.json")["texture_data"])

ALIAS = {"grass_block": "grass", "sea_lantern": "seaLantern", "iron_chain": "chain", "darkoak_wall_sign": "darkoak_wall_sign",
         "standing_sign": "standing_sign", "wall_sign": "wall_sign", "noteblock": "noteblock"}

# 染料顏色（Java 的順序：0 白 … 15 黑）
DYE = [(249, 255, 254), (249, 128, 29), (199, 78, 189), (58, 179, 218), (254, 216, 61), (128, 199, 31), (243, 139, 170),
       (71, 79, 82), (157, 157, 151), (22, 156, 156), (137, 50, 184), (60, 68, 170), (131, 84, 50), (94, 124, 22),
       (176, 46, 38), (29, 29, 33)]
# 基岩版旗幟用舊的染料編號：0 黑、1 紅、2 綠、3 棕、4 藍、5 紫、6 青、7 淺灰、8 灰、9 粉紅、10 黃綠、11 黃、12 淺藍、13 洋紅、14 橘、15 白
BANNER_TO_DYE = [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]

# ── 材質 ────────────────────────────────────────────────

TEX_LIST, TEX_INDEX = [], {}


def tex_file(path):
    """材質路徑（不含副檔名）→ 實際檔案；資源包優先於原版。"""
    for root in (DEVRP, BS):
        if root is None:
            continue
        for ext in (".png", ".tga"):
            f = root / (path + ext)
            if f.exists():
                return f
    return None


def tex_id(path):
    """登記一張材質，回傳在材質拼圖裡的編號；找不到檔案回傳 None。"""
    if path is None:
        return None
    if path in TEX_INDEX:
        return TEX_INDEX[path]
    f = tex_file(path)
    if f is None:
        TEX_INDEX[path] = None
        return None
    TEX_INDEX[path] = len(TEX_LIST)
    TEX_LIST.append((path, f))
    return TEX_INDEX[path]


def tex_image(key, img):
    """登記一張程式產生的材質（例如從實體材質切出來的置物櫃門）。"""
    if key not in TEX_INDEX:
        TEX_INDEX[key] = len(TEX_LIST)
        TEX_LIST.append((key, img))
    return TEX_INDEX[key]


def locker_textures(color):
    """Asuka tech 把界伏蚌盒換成置物櫃：門畫在蓋子頂面，四周是側板。"""
    name = {"white": "white", "light_gray": "silver"}.get(color, color)
    if DEVRP is None:
        return None
    f = DEVRP / "textures" / "entity" / "shulker" / f"shulker_{name}.png"
    if not f.exists():
        return None
    img = Image.open(f).convert("RGBA")
    door = img.crop((16, 0, 32, 16))
    side = Image.new("RGBA", (16, 16))
    side.paste(img.crop((0, 16, 16, 24)), (0, 0))
    side.paste(img.crop((0, 52, 16, 60)), (0, 8))
    return tex_image(f"locker_door_{name}", door), tex_image(f"locker_side_{name}", side)


def terrain_path(key, variant=0):
    e = TERRAIN.get(key)
    if e is None:
        return None
    t = e.get("textures")
    if isinstance(t, list):
        t = t[min(variant, len(t) - 1)] if t else None
    if isinstance(t, dict):
        t = t.get("path")
    return t


def block_faces(name):
    """方塊名稱 → 六個面的材質路徑 {up, down, north, south, east, west}；查不到回傳 None。"""
    e = BLOCKS.get(name) or BLOCKS.get(ALIAS.get(name, ""))
    if not e or "textures" not in e:
        return None
    t = e["textures"]
    if isinstance(t, str):
        p = terrain_path(t)
        return {f: p for f in ("up", "down", "north", "south", "east", "west")} if p else None
    side = t.get("side")
    out = {}
    for f in ("up", "down", "north", "south", "east", "west"):
        k = t.get(f) or side or t.get("up")
        out[f] = terrain_path(k) if k else None
    if not any(out.values()):
        return None
    for f in out:
        if out[f] is None:
            out[f] = next(v for v in out.values() if v)
    return out


def faces_of(*names):
    for n in names:
        f = block_faces(n)
        if f:
            return f
    return None


def uniform(path):
    return {f: path for f in ("up", "down", "north", "south", "east", "west")}


# 半磚、樓梯、牆的材質要借用「本體」方塊
BASE_FIX = {"quartz": "quartz_block", "smooth_quartz": "smooth_quartz", "stone_brick": "stone_bricks", "normal_stone": "stone",
            "stone": "stone", "smooth_stone": "smooth_stone", "birch": "birch_planks", "oak": "oak_planks", "spruce": "spruce_planks",
            "dark_oak": "dark_oak_planks", "acacia": "acacia_planks", "pale_oak": "pale_oak_planks", "crimson": "crimson_planks",
            "deepslate_tile": "deepslate_tiles", "deepslate_brick": "deepslate_bricks", "polished_andesite": "polished_andesite",
            "andesite": "andesite", "polished_blackstone": "polished_blackstone", "dark_prismarine": "dark_prismarine",
            "waxed_cut_copper": "waxed_cut_copper", "polished_deepslate": "polished_deepslate", "cobblestone": "cobblestone"}


def base_block(stem):
    if stem in BASE_FIX:
        return BASE_FIX[stem]
    return stem


# ── 形狀 ────────────────────────────────────────────────
# 方塊內的座標用 1/16 為單位。面的順序：0 東(+X) 1 西(-X) 2 上(+Y) 3 下(-Y) 4 南(+Z) 5 北(-Z)
FACE_ORDER = ("east", "west", "up", "down", "south", "north")
DIR4 = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}
FACING6 = {0: "down", 1: "up", 2: "north", 3: "south", 4: "west", 5: "east"}
CARD = ["south", "west", "north", "east"]  # 告示牌 ground_sign_direction / 4 的方向


def against(side, depth, y0=0, y1=16, a0=0, a1=16):
    """貼著方塊某一側、厚度 depth 的板子。a0..a1 是沿牆的範圍。"""
    if side == "north":
        return [a0, y0, 0, a1, y1, depth]
    if side == "south":
        return [a0, y0, 16 - depth, a1, y1, 16]
    if side == "west":
        return [0, y0, a0, depth, y1, a1]
    if side == "east":
        return [16 - depth, y0, a0, 16, y1, a1]
    raise ValueError(side)


def centered_board(facing, y0, y1, thick=2, a0=0, a1=16):
    """方塊中間、面向 facing 的板子（直立告示牌、旗幟）。"""
    h = thick / 2
    if facing in ("south", "north"):
        return [a0, y0, 8 - h, a1, y1, 8 + h]
    return [8 - h, y0, a0, 8 + h, y1, a1]


OPP = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
ROT_CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
ROT_CCW = {v: k for k, v in ROT_CW.items()}

TRANSLUCENT_WORDS = ("stained_glass", "ice", "tinted_glass", "slime", "honey_block")
CUTOUT_WORDS = ("glass", "leaves", "iron_bars", "rail", "door", "trapdoor", "scaffolding", "mob_spawner", "chain", "lantern",
                "cauldron", "hopper", "brewing_stand", "beacon", "end_rod", "torch", "ladder", "vine", "redstone_wire", "fence",
                "frame", "bars", "copper_golem", "turtle_egg", "candle", "cake", "campfire", "tripwire", "lever", "sea_pickle",
                "dried_ghast", "barrel", "shelf")
INVISIBLE = {"air", "barrier", "structure_void", "light_block", "moving_block", "piston_arm_collision", "sticky_piston_arm_collision"}
PLANTS = {"short_grass": "tallgrass", "tall_grass": "double_plant_grass_top", "fern": "fern", "dandelion": "flower_dandelion",
          "deadbush": "deadbush", "bush": "bush", "brown_mushroom": "mushroom_brown", "red_mushroom": "mushroom_red",
          "dead_fire_coral": "coral_fan_dead"}
TINT = {"grass": (124, 189, 107), "leaves": (89, 174, 48), "spruce_leaves": (97, 153, 97), "water": (63, 118, 228)}


def spec_for(name, states):
    """一種方塊（含狀態）→ 給網頁用的形狀說明。"""
    short = name.split(":")[-1]
    s = states or {}
    spec = {"n": short}
    if short in INVISIBLE or short.startswith("light_block"):
        spec["k"] = "none"
        return spec

    mat = 0
    if any(w in short for w in TRANSLUCENT_WORDS) or short in ("water", "lava"):
        mat = 2
    elif any(w in short for w in CUTOUT_WORDS):
        mat = 1
    spec["m"] = mat
    if "glass" in short or short in ("iron_bars",):
        spec["g"] = 1

    faces = None
    boxes = None
    kind = "cube"

    # ── 先決定材質 ──
    if short == "grass_block":
        faces = {"up": "textures/blocks/grass_top", "down": "textures/blocks/dirt", **{f: "textures/blocks/grass_side_carried" for f in ("north", "south", "east", "west")}}
        spec["tt"] = list(TINT["grass"])  # 只染頂面
    elif short.endswith("_door"):
        wood = {"birch_door": "birch", "spruce_door": "spruce", "dark_oak_door": "dark_oak", "iron_door": "iron", "acacia_door": "acacia",
                "jungle_door": "jungle", "pale_oak_door": "pale_oak", "wooden_door": "wood"}.get(short, short.replace("_door", ""))
        part = "upper" if s.get("upper_block_bit") else "lower"
        p = f"textures/blocks/door_{wood}_{part}"
        if tex_file(p) is None:
            p = f"textures/blocks/{wood}_door_{part}"
        faces = uniform(p)
    elif short in PLANTS:
        faces = uniform(terrain_path(PLANTS[short]) or f"textures/blocks/{PLANTS[short]}")
    elif "_slab" in short or short.endswith("_stairs") or short.endswith("_wall") or short.endswith("_fence") or short == "fence_gate" or short.endswith("_fence_gate"):
        faces = block_faces(short)
        if faces is None:
            stem = re.sub(r"_(double_slab|slab|stairs|wall|fence_gate|fence)$", "", short)
            faces = faces_of(base_block(stem), stem + "s", stem + "_planks", stem + "_block")
        if short == "fence_gate":
            faces = block_faces("oak_planks")
    elif short.endswith("_carpet"):
        faces = faces_of(short.replace("_carpet", "_wool"))
    elif short.endswith("_wall_sign") or short.endswith("_standing_sign") or short in ("wall_sign", "standing_sign") or short.endswith("_hanging_sign"):
        wood = short.replace("_wall_sign", "").replace("_standing_sign", "").replace("_hanging_sign", "")
        wood = {"wall_sign": "oak", "standing_sign": "oak", "darkoak": "dark_oak"}.get(wood, wood)
        faces = faces_of(f"{wood}_planks") or block_faces("oak_planks")
    elif short in ("wall_banner", "standing_banner"):
        faces = uniform("__white__")
    elif short == "bed":
        faces = uniform("__white__")
    elif short in ("frame", "glow_frame"):
        faces = uniform("textures/blocks/itemframe_background")
    elif short == "water":
        faces = uniform("textures/blocks/still_water_grey")
        spec["t_all"] = list(TINT["water"])
    elif short == "lava":
        faces = uniform(terrain_path("still_lava") or "textures/blocks/lava_still")
    elif short in ("chest",):
        faces = {"up": "textures/blocks/chest_top", "down": "textures/blocks/chest_top", **{f: "textures/blocks/chest_side" for f in ("north", "south", "east", "west")}}
        faces["south"] = "textures/blocks/chest_front"
    elif short.endswith("copper_golem_statue"):
        faces = faces_of("copper_block") or uniform("__white__")
    elif short == "wither_skeleton_skull":
        faces = faces_of("coal_block")
    elif short.endswith("_shulker_box") and locker_textures(short.replace("_shulker_box", "")):
        door, side = locker_textures(short.replace("_shulker_box", ""))
        spec["door"] = door
        spec["t"] = [side] * 6
        spec["k"], spec["o"], spec["m"] = "cube", 1, 0
        return spec
    elif short in ("lantern", "soul_lantern"):
        faces = uniform("__white__")
        spec["t_all"] = [255, 196, 110] if short == "lantern" else [120, 220, 230]
    elif short == "asukatech:conveyor" or short == "conveyor":
        faces = None
    else:
        faces = block_faces(short)
        if faces is None:
            faces = faces_of(short + "_block", short.replace("_block", ""), base_block(short))

    if name.startswith("asukatech:"):
        folder = DEVRP / "textures" / "blocks" / "asukatech" if DEVRP else None
        files = sorted(folder.glob(f"*{short}*.png")) if folder and folder.exists() else []
        faces = uniform(str(files[0].relative_to(DEVRP).with_suffix("")).replace("\\", "/")) if files else uniform("textures/blocks/iron_block")
        boxes = [[0, 0, 0, 16, 4, 16]]
        kind = "boxes"

    # 染色
    if short.endswith("leaves"):
        spec["t_all"] = list(TINT["spruce_leaves" if short.startswith("spruce") else "leaves"])
    if short in ("short_grass", "tall_grass", "fern", "vine"):
        spec["t_all"] = list(TINT["grass"])

    # ── 再決定形狀 ──
    up = bool(s.get("upside_down_bit"))
    if short in PLANTS:
        kind = "cross"
    elif short.endswith("_double_slab"):
        kind = "cube"
    elif "_slab" in short:
        top = s.get("minecraft:vertical_half") == "top" or s.get("top_slot_bit")
        boxes, kind = [[0, 8, 0, 16, 16, 16] if top else [0, 0, 0, 16, 8, 16]], "boxes"
    elif short.endswith("_stairs"):
        d = ["east", "west", "south", "north"][s.get("weirdo_direction", 0)]
        half = [0, 8, 0, 16, 16, 16] if up else [0, 0, 0, 16, 8, 16]
        y0, y1 = (0, 8) if up else (8, 16)
        back = {"east": [8, y0, 0, 16, y1, 16], "west": [0, y0, 0, 8, y1, 16], "south": [0, y0, 8, 16, y1, 16], "north": [0, y0, 0, 16, y1, 8]}[d]
        boxes, kind = [half, back], "boxes"
    elif short.endswith("_carpet") or short == "snow_layer":
        h = 1 if short.endswith("_carpet") else 2 * (s.get("height", 0) + 1)
        boxes, kind = [[0, 0, 0, 16, h, 16]], "boxes"
    elif short.endswith("pressure_plate"):
        boxes, kind = [[1, 0, 1, 15, 1, 15]], "boxes"
    elif short in ("rail", "golden_rail", "redstone_wire", "detector_rail", "activator_rail", "tripwire"):
        boxes, kind = [[0, 0, 0, 16, 1, 16]], "boxes"
        if short in ("rail", "golden_rail"):
            p = terrain_path("rail_normal") if short == "rail" else terrain_path("rail_golden")
            faces = uniform(p or "textures/blocks/rail_normal")
    elif short in ("unpowered_repeater", "unpowered_comparator", "powered_repeater", "powered_comparator"):
        boxes, kind = [[0, 0, 0, 16, 2, 16]], "boxes"
        faces = uniform("textures/blocks/smooth_stone")
    elif short.endswith("_fence"):
        kind = "fence"
    elif short == "fence_gate" or short.endswith("_fence_gate"):
        d = s.get("direction", 0)
        along_x = d in (0, 2)  # 0 南 1 西 2 北 3 東：門板沿著 X
        if s.get("open_bit"):
            along_x = not along_x
        boxes = [[0, 6, 7, 16, 15, 9]] if along_x else [[7, 6, 0, 9, 15, 16]]
        boxes += [[0, 5, 7, 2, 16, 9], [14, 5, 7, 16, 16, 9]] if along_x else [[7, 5, 0, 9, 16, 2], [7, 5, 14, 9, 16, 16]]
        kind = "boxes"
    elif short.endswith("_wall") and "sign" not in short and "banner" not in short:
        kind = "wall"
        b = []
        if s.get("wall_post_bit", 1):
            b.append([4, 0, 4, 12, 16, 12])
        for side, (dx, dz) in DIR4.items():
            t = s.get(f"wall_connection_type_{side}", "none")
            if t == "none":
                continue
            h = 16 if t == "tall" else 14
            if side == "north":
                b.append([5, 0, 0, 11, h, 8])
            elif side == "south":
                b.append([5, 0, 8, 11, h, 16])
            elif side == "west":
                b.append([0, 0, 5, 8, h, 11])
            else:
                b.append([8, 0, 5, 16, h, 11])
        boxes, kind = b or [[4, 0, 4, 12, 16, 12]], "boxes"
    elif "glass_pane" in short or short == "iron_bars":
        kind = "pane"
    elif short in ("iron_chain", "chain"):
        ax = s.get("pillar_axis", "y")
        boxes = {"y": [[7, 0, 7, 9, 16, 9]], "x": [[0, 7, 7, 16, 9, 9]], "z": [[7, 7, 0, 9, 9, 16]]}[ax]
        kind = "boxes"
    elif short in ("lantern", "soul_lantern"):
        y = 1 if s.get("hanging") else 0
        boxes, kind = [[5, y, 5, 11, y + 7, 11], [6, y + 7, 6, 10, y + 9, 10]], "boxes"
    elif short == "end_rod":
        f = FACING6.get(s.get("facing_direction", 1), "up")
        boxes = [[7, 0, 7, 9, 16, 9]] if f in ("up", "down") else ([[0, 7, 7, 16, 9, 9]] if f in ("east", "west") else [[7, 7, 0, 9, 9, 16]])
        kind = "boxes"
    elif short in ("torch", "redstone_torch", "soul_torch"):
        boxes, kind = [[7, 0, 7, 9, 10, 9]], "boxes"
    elif short.endswith("_button") or short == "stone_button":
        f = FACING6.get(s.get("facing_direction", 1), "up")
        if f == "up":
            boxes = [[5, 0, 6, 11, 2, 10]]
        elif f == "down":
            boxes = [[5, 14, 6, 11, 16, 10]]
        else:
            boxes = [against(OPP[f], 2, 6, 10, 5, 11)]
        kind = "boxes"
    elif short in ("lever", "tripwire_hook"):
        boxes, kind = [[6, 0, 6, 10, 6, 10]], "boxes"
    elif short in ("ladder", "vine"):
        f = FACING6.get(s.get("facing_direction", 2), "north") if short == "ladder" else "north"
        boxes, kind = [against(OPP.get(f, "north"), 1)], "boxes"
    elif short.endswith("_door"):
        d = ["east", "south", "west", "north"][s.get("direction", 0)]
        side = OPP[d]
        if s.get("open_bit"):
            side = ROT_CW[side] if s.get("door_hinge_bit") else ROT_CCW[side]
        boxes, kind = [against(side, 3)], "boxes"
    elif short.endswith("trapdoor"):
        d = ["east", "west", "south", "north"][s.get("direction", 0)]
        if s.get("open_bit"):
            boxes = [against(OPP[d], 3)]
        else:
            boxes = [[0, 13, 0, 16, 16, 16]] if up else [[0, 0, 0, 16, 3, 16]]
        kind = "boxes"
    elif short in ("frame", "glow_frame"):
        f = FACING6.get(s.get("facing_direction", 2), "north")
        if f == "up":
            boxes = [[2, 0, 2, 14, 1, 14]]
        elif f == "down":
            boxes = [[2, 15, 2, 14, 16, 14]]
        else:
            boxes = [against(OPP[f], 1, 2, 14, 2, 14)]
        kind = "boxes"
    elif short.endswith("wall_sign") or short == "wall_sign":
        f = FACING6.get(s.get("facing_direction", 2), "north")
        boxes, kind = [against(OPP[f], 2, 4, 12)], "boxes"
        spec["sign"] = ["wall", f]
    elif short.endswith("standing_sign"):
        f = CARD[round(s.get("ground_sign_direction", 0) / 4) % 4]
        boxes, kind = [centered_board(f, 8, 16), [7, 0, 7, 9, 8, 9]], "boxes"
        spec["sign"] = ["stand", f]
    elif short.endswith("hanging_sign"):
        if s.get("hanging", 1) and s.get("attached_bit"):
            f = CARD[round(s.get("ground_sign_direction", 0) / 4) % 4]
        else:
            f = FACING6.get(s.get("facing_direction", 2), "north")
            if f in ("up", "down"):
                f = "north"
        if s.get("hanging", 1):
            boxes = [centered_board(f, 0, 10, 2, 1, 15)]
        else:
            boxes = [against(OPP[f], 2, 2, 12, 1, 15)]
        kind = "boxes"
        spec["sign"] = ["hang", f]
    elif short == "wall_banner":
        f = FACING6.get(s.get("facing_direction", 2), "north")
        boxes, kind = [against(OPP[f], 1, -16, 14, 1, 15), against(OPP[f], 2, 14, 16, 0, 16)], "boxes"
        spec["banner"] = ["wall", f]
    elif short == "standing_banner":
        f = CARD[round(s.get("ground_sign_direction", 0) / 4) % 4]
        cloth = centered_board(f, 10, 42, 1, 1, 15)
        dx, dz = DIR4[f]
        cloth = [cloth[0] + 1.5 * dx, cloth[1], cloth[2] + 1.5 * dz, cloth[3] + 1.5 * dx, cloth[4], cloth[5] + 1.5 * dz]  # 布在旗桿前面
        bar = [1, 42, 7, 15, 44, 9] if f in ("south", "north") else [7, 42, 1, 9, 44, 15]
        boxes = [cloth, [7, 0, 7, 9, 42, 9], bar]
        kind = "boxes"
        spec["banner"] = ["stand", f]
    elif short == "bed":
        boxes, kind = [[0, 0, 0, 16, 9, 16]], "boxes"
        spec["bed"] = 1
    elif short in ("cake",):
        boxes, kind = [[1, 0, 1, 15, 8, 15]], "boxes"
    elif short in ("campfire",):
        boxes, kind = [[0, 0, 0, 16, 7, 16]], "boxes"
    elif short in ("turtle_egg", "sea_pickle", "red_candle", "candle", "dried_ghast") or short.endswith("copper_golem_statue"):
        boxes, kind = [[4, 0, 4, 12, 10, 12]], "boxes"
    elif short == "wither_skeleton_skull":
        boxes, kind = [[4, 0, 4, 12, 8, 12]], "boxes"
    elif short in ("hopper",):
        boxes, kind = [[0, 10, 0, 16, 16, 16], [4, 4, 4, 12, 10, 12]], "boxes"
    elif short in ("brewing_stand",):
        boxes, kind = [[7, 0, 7, 9, 14, 9], [1, 0, 1, 15, 2, 15]], "boxes"
    elif short in ("anvil", "grindstone", "lectern"):
        boxes, kind = [[2, 0, 2, 14, 12, 14]], "boxes"
    elif short == "cactus":
        boxes, kind = [[1, 0, 1, 15, 16, 15]], "boxes"
    elif short.endswith("_shelf"):
        f = {0: "south", 1: "west", 2: "north", 3: "east"}.get(s.get("direction", 0), "south")
        boxes, kind = [against(OPP[f], 8)], "boxes"
    elif short.endswith("_head") or short.endswith("_skull"):
        boxes, kind = [[4, 0, 4, 12, 8, 12]], "boxes"

    # 柱狀方塊的方向
    ax = s.get("pillar_axis")
    if faces and ax in ("x", "z") and kind == "cube":
        top, side = faces["up"], faces["north"]
        faces = {f: side for f in faces}
        if ax == "x":
            faces["east"] = faces["west"] = top
        else:
            faces["north"] = faces["south"] = top

    if faces is None:
        faces = uniform("__unknown__")
        spec["unknown"] = 1
    spec["t"] = [tex_id(faces[f]) if faces[f] not in ("__white__", "__unknown__") else faces[f] for f in FACE_ORDER]
    spec["k"] = kind
    if boxes is not None:
        spec["b"] = boxes
    if kind == "cube" and mat == 0:
        spec["o"] = 1  # 完全擋住視線的方塊
    if short in ("water",):
        spec["k"] = "boxes"
        spec["b"] = [[0, 0, 0, 16, 14, 16]]
    return spec


def build_atlas():
    """所有用到的材質排成一張拼圖，每格 16 像素，四周補 2 像素邊（避免邊緣滲色）。"""
    CELL, PAD = 20, 2
    specials = ["__white__", "__unknown__"]
    n = len(TEX_LIST) + len(specials)
    cols = 32
    rows = (n + cols - 1) // cols
    atlas = Image.new("RGBA", (cols * CELL, rows * CELL), (0, 0, 0, 0))
    avg = []

    def place(i, img):
        img = img.convert("RGBA")
        w, h = img.size
        if h > w:  # 動畫材質：取第一格
            img = img.crop((0, 0, w, w))
        img = img.resize((16, 16), Image.NEAREST)
        x, y = (i % cols) * CELL, (i // cols) * CELL
        padded = Image.new("RGBA", (CELL, CELL))
        # 邊緣像素往外延伸
        big = img.resize((16, 16))
        padded.paste(big, (PAD, PAD))
        for k in range(PAD):
            padded.paste(big.crop((0, 0, 16, 1)), (PAD, k))
            padded.paste(big.crop((0, 15, 16, 16)), (PAD, PAD + 16 + k))
        left = padded.crop((PAD, 0, PAD + 1, CELL))
        right = padded.crop((PAD + 15, 0, PAD + 16, CELL))
        for k in range(PAD):
            padded.paste(left, (k, 0))
            padded.paste(right, (PAD + 16 + k, 0))
        atlas.paste(padded, (x, y))
        a = np.asarray(img).astype(float)
        m = a[..., 3] > 0
        avg.append([int(v) for v in (a[..., :3][m].mean(0) if m.any() else [128, 128, 128])])

    for i, (_, f) in enumerate(TEX_LIST):
        place(i, f if isinstance(f, Image.Image) else Image.open(f))
    place(len(TEX_LIST), Image.new("RGBA", (16, 16), (255, 255, 255, 255)))
    unk = Image.new("RGBA", (16, 16), (200, 0, 200, 255))
    place(len(TEX_LIST) + 1, unk)
    buf = io.BytesIO()
    atlas.save(buf, "PNG", optimize=True)
    return {"png": base64.b64encode(buf.getvalue()).decode(), "cols": cols, "cell": CELL, "pad": PAD,
            "w": atlas.width, "h": atlas.height, "white": len(TEX_LIST), "unknown": len(TEX_LIST) + 1}, avg


# ── 畫 ──────────────────────────────────────────────────
# 舊的畫都在 kz.png（原版 256 像素寬，每格 16 像素），(x, y, 寬, 高) 以格為單位
KZ = {"Kebab": (0, 0, 1, 1), "Aztec": (1, 0, 1, 1), "Alban": (2, 0, 1, 1), "Aztec2": (3, 0, 1, 1), "Bomb": (4, 0, 1, 1),
      "Plant": (5, 0, 1, 1), "Wasteland": (6, 0, 1, 1), "Pool": (0, 2, 2, 1), "Courbet": (2, 2, 2, 1), "Sea": (4, 2, 2, 1),
      "Sunset": (6, 2, 2, 1), "Creebet": (8, 2, 2, 1), "Wanderer": (0, 4, 1, 2), "Graham": (1, 4, 1, 2), "Match": (0, 8, 2, 2),
      "Bust": (2, 8, 2, 2), "Stage": (4, 8, 2, 2), "Void": (6, 8, 2, 2), "SkullAndRoses": (8, 8, 2, 2), "Wither": (10, 8, 2, 2),
      "Fighters": (0, 6, 4, 2), "Pointer": (0, 12, 4, 4), "Pigscene": (4, 12, 4, 4), "BurningSkull": (8, 12, 4, 4),
      "Skeleton": (12, 4, 4, 3), "DonkeyKong": (12, 7, 4, 3), "Earth": (0, 10, 2, 2), "Wind": (2, 10, 2, 2), "Water": (4, 10, 2, 2),
      "Fire": (6, 10, 2, 2)}
NEW = {"backyard": (3, 4), "baroque": (2, 2), "bouquet": (3, 3), "cavebird": (3, 3), "changing": (4, 2), "cotan": (3, 3),
       "endboss": (3, 3), "fern": (3, 3), "finding": (4, 2), "humble": (2, 2), "lowmist": (4, 2), "meditative": (1, 1),
       "orb": (4, 4), "owlemons": (3, 3), "passage": (4, 2), "pond": (3, 4), "prairie_ride": (1, 2), "sunflowers": (3, 3),
       "tides": (3, 3), "unpacked": (4, 4)}


def painting_images(motifs, px=48):
    """把用到的畫切出來排成一張圖，每格 px 像素。回傳 (圖, {名稱: [u0,v0,u1,v1,寬,高]})。"""
    kz_path = DEVRP / "textures" / "painting" / "kz.png" if DEVRP else None
    kz = Image.open(kz_path if kz_path and kz_path.exists() else BS / "textures" / "painting" / "kz.png").convert("RGBA")
    unit = kz.width // 16
    tiles = []
    for m in sorted(motifs):
        if m in KZ:
            x, y, w, h = KZ[m]
            img = kz.crop((x * unit, y * unit, (x + w) * unit, (y + h) * unit))
        elif m.lower() in NEW:
            w, h = NEW[m.lower()]
            f = DEVRP / "textures" / "painting" / f"{m.lower()}.png" if DEVRP else None
            if not f or not f.exists():
                f = BS / "textures" / "painting" / f"{m.lower()}.png"
            img = Image.open(f).convert("RGBA")
        else:
            continue
        tiles.append((m, w, h, img.resize((w * px, h * px), Image.LANCZOS)))
    width = 16 * px
    x = y = rowh = 0
    pos = {}
    for m, w, h, img in tiles:
        if x + w * px > width:
            x, y, rowh = 0, y + rowh, 0
        pos[m] = (x, y, w, h)
        x += w * px
        rowh = max(rowh, h * px)
    height = y + rowh
    sheet = Image.new("RGBA", (width, max(height, 1)))
    for m, w, h, img in tiles:
        sheet.paste(img, pos[m][:2])
    uv = {m: [x / width, 1 - (y + h * px) / height, (x + w * px) / width, 1 - y / height, w, h] for m, (x, y, w, h) in pos.items()}
    buf = io.BytesIO()
    sheet.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), uv


BANNER_FILES = {"b": "base", "bl": "square_bottom_left", "br": "square_bottom_right", "tl": "square_top_left", "tr": "square_top_right",
                "bs": "stripe_bottom", "ts": "stripe_top", "ls": "stripe_left", "rs": "stripe_right", "cs": "stripe_center",
                "ms": "stripe_middle", "drs": "stripe_downright", "dls": "stripe_downleft", "ss": "small_stripes", "cr": "cross",
                "sc": "straight_cross", "bt": "triangle_bottom", "tt": "triangle_top", "bts": "triangles_bottom", "tts": "triangles_top",
                "ld": "diagonal_left", "rd": "diagonal_up_right", "lud": "diagonal_up_left", "rud": "diagonal_right", "mc": "circle",
                "mr": "rhombus", "vh": "half_vertical", "hh": "half_horizontal", "vhr": "half_vertical_right", "hhb": "half_horizontal_bottom",
                "bo": "border", "cbo": "curly_border", "gra": "gradient", "gru": "gradient_up", "bri": "bricks", "glb": "globe",
                "cre": "creeper", "sku": "skull", "flo": "flower", "moj": "mojang", "pig": "piglin", "flw": "flow", "gus": "guster"}
_BANNER_CACHE = {}


def banner_layer(code):
    if code not in _BANNER_CACHE:
        img = None
        for ext in (".png", ".tga"):
            f = BS / "textures" / "entity" / "banner" / f"banner_{BANNER_FILES.get(code, code)}{ext}"
            if f.exists():
                img = np.asarray(Image.open(f).convert("RGBA")).astype(float)[1:41, 1:21] / 255
                break
        _BANNER_CACHE[code] = img
    return _BANNER_CACHE[code]


def banner_atlas(banners):
    """每一種旗幟（底色＋圖樣）畫成 20 × 40 的正面圖，排成一張圖。"""
    combos, index = [], {}
    for key, (base, pats) in banners.items():
        sig = json.dumps([base, pats])
        if sig not in index:
            index[sig] = len(combos)
            combos.append((base, pats))
        banners[key] = [base, index[sig]]
    cols = 25
    rows = max(1, (len(combos) + cols - 1) // cols)
    sheet = np.zeros((rows * 40, cols * 20, 4))
    shade = banner_layer("b")
    for i, (base, pats) in enumerate(combos):
        img = np.ones((40, 20, 3)) * np.array(base) / 255 * shade[..., :3]
        for code, color in pats:
            layer = banner_layer(code)
            if layer is None:
                continue
            a = layer[..., 3:4]
            img = img * (1 - a) + (np.array(color) / 255 * layer[..., :3]) * a
        y, x = (i // cols) * 40, (i % cols) * 20
        sheet[y:y + 40, x:x + 20, :3] = img
        sheet[y:y + 40, x:x + 20, 3] = 1
    buf = io.BytesIO()
    Image.fromarray((sheet * 255).round().astype(np.uint8)).save(buf, "PNG", optimize=True)
    return {"png": base64.b64encode(buf.getvalue()).decode(), "cols": cols, "rows": rows}


def clean_text(t):
    return re.sub(r"§.", "", t or "")


def argb(v):
    v &= 0xFFFFFFFF
    return "#%06x" % (v & 0xFFFFFF)


def three_classic():
    """three.js 的兩個 ES 模組改成一般 <script> 用的寫法，網頁雙擊就能開（不用網路、不用伺服器）。"""
    core = (THREE / "three.core.js").read_text(encoding="utf-8")
    mod = (THREE / "three.module.js").read_text(encoding="utf-8")
    m = re.search(r"^export \{([^}]*)\};\s*$", core, flags=re.M)
    core_names = [n.strip() for n in m.group(1).split(",") if n.strip()]
    core = core[:m.start()] + core[m.end():]
    lines = mod.split("\n")
    imp = [i for i, l in enumerate(lines) if l.startswith("import {") and "three.core.js" in l]
    reexp = [i for i, l in enumerate(lines) if l.startswith("export {") and "three.core.js" in l]
    imported = re.search(r"import \{([^}]*)\}", lines[imp[0]]).group(1)
    imported = [n.strip() for n in imported.split(",") if n.strip()]
    for i in imp + reexp:
        lines[i] = ""
    mod = "\n".join(lines)
    m2 = re.search(r"^export \{([^}]*)\};\s*$", mod, flags=re.M)
    mod_names = [n.strip() for n in m2.group(1).split(",") if n.strip()]
    mod = mod[:m2.start()] + mod[m2.end():]
    if "import.meta" in core or "import.meta" in mod or re.search(r"^\s*(import|export)\b", core + mod, flags=re.M):
        raise SystemExit("three.js 的模組格式和預期不同，請檢查")
    return ("(function(){'use strict';\nconst __CORE=(function(){\n" + core + "\nreturn {" + ",".join(core_names) + "};\n})();\n"
            "const {" + ",".join(imported) + "}=__CORE;\n"
            "const __MOD=(function(){\n" + mod + "\nreturn {" + ",".join(mod_names) + "};\n})();\n"
            "window.THREE=Object.assign({},__CORE,__MOD);\n})();\n")


def load_preset(name):
    """範圍設定：presets/<名稱>.json，或直接給 .json 的路徑。"""
    path = Path(name) if name.endswith(".json") else HERE / "presets" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="把讀出的方塊資料做成 3D 模型網頁")
    parser.add_argument("data", help="extract.py 的輸出資料夾")
    parser.add_argument("--preset", required=True, help="範圍設定（標題、樓層、參考點），例如 akq")
    parser.add_argument("--out", required=True, help="輸出的網頁檔名")
    parser.add_argument("--pack", help="資源包資料夾；不指定時依世界掛的資源包到 addon/build/ 裡找")
    args = parser.parse_args()
    data_dir, out = Path(args.data), Path(args.out)
    preset = load_preset(args.preset)
    if not THREE.exists():
        raise SystemExit("找不到 three.js，請先在 tools/preview 執行 npm install。")
    ensure_samples()
    meta = json.loads((data_dir / "meta.json").read_text(encoding="utf-8"))
    pack = Path(args.pack) if args.pack else find_pack(meta.get("resource_packs", []))
    print(f"資源包：{pack}" if pack else "★找不到世界掛的資源包（addon/build/ 裡沒有組好的包），只用原版材質")
    load_packs(pack)
    grid = np.load(data_dir / "region.npz")["grid"]
    x0, y0, z0 = meta["origin"]
    sx, sy, sz = meta["size"]

    palette = [spec_for(p["name"], p["states"]) for p in meta["palette"]]
    atlas, avg = build_atlas()
    for spec in palette:
        spec["t"] = [atlas["white"] if t == "__white__" else atlas["unknown"] if (t == "__unknown__" or t is None) else t for t in spec.get("t", [])]

    unknown = sorted({p["n"] for p in palette if p.get("unknown")})
    print("找不到材質的方塊：", unknown)

    be = json.loads((data_dir / "block_entities.json").read_text(encoding="utf-8"))
    signs, banners, beds, shulkers = [], {}, {}, {}
    for e in be:
        key = f"{e['x']},{e['y']},{e['z']}"
        if e.get("id") in ("Sign", "HangingSign"):
            ft, bt = e.get("FrontText") or {}, e.get("BackText") or {}
            f, b = clean_text(ft.get("Text")), clean_text(bt.get("Text"))
            if f.strip() or b.strip():
                signs.append([e["x"], e["y"], e["z"], f, argb(ft.get("SignTextColor", -16777216)), b, argb(bt.get("SignTextColor", -16777216))])
        elif e.get("id") == "Banner":
            base = DYE[BANNER_TO_DYE[e.get("Base", 15) % 16]]
            pats = [[p.get("Pattern"), DYE[BANNER_TO_DYE[p.get("Color", 0) % 16]]] for p in e.get("Patterns") or []]
            banners[key] = [base, pats]
        elif e.get("id") == "Bed":
            beds[key] = DYE[e.get("color", 14) % 16]
        elif e.get("id") == "ShulkerBox":
            shulkers[key] = e.get("facing", 1)

    ents = json.loads((data_dir / "entities.json").read_text(encoding="utf-8"))
    paintings, people, stands, carts = [], [], [], []
    for e in ents:
        i, pos = e["identifier"], e.get("Pos") or [0, 0, 0]
        yaw = (e.get("Rotation") or [0, 0])[0]
        if i == "minecraft:painting":
            paintings.append([pos[0], pos[1], pos[2], e.get("Direction", 0), e.get("Motif")])
        elif i == "minecraft:npc":
            people.append([pos[0], pos[1], pos[2], yaw, e.get("Variant", 0)])
        elif i == "minecraft:armor_stand":
            arm = [a.get("Name", "") if isinstance(a, dict) else "" for a in (e.get("Armor") or [])]
            hands = [a for a in (e.get("Mainhand") or []) if isinstance(a, dict)]
            hand = hands[0].get("Name", "") if hands else ""
            shield = None
            if hand == "minecraft:shield":
                tag = hands[0].get("tag") or {}
                shield = DYE[BANNER_TO_DYE[tag["Base"] % 16]] if "Base" in tag else [150, 110, 70]
            stands.append([pos[0], pos[1], pos[2], yaw, arm[0] if arm else "", arm[2] if len(arm) > 2 else "", hand, shield])
        elif "minecart" in i:
            carts.append([pos[0], pos[1], pos[2], yaw, i.split(":")[-1]])
    ptex, puv = painting_images({p[4] for p in paintings})
    batlas = banner_atlas(banners)

    D = {
        "origin": [x0, y0, z0], "size": [sx, sy, sz],
        "grid": base64.b64encode(zlib.compress(grid.astype("<u2").tobytes(), 9)).decode(),
        "pal": palette, "atlas": atlas, "avg": avg,
        "signs": signs, "banners": banners, "batlas": batlas, "beds": beds, "shulkers": shulkers,
        "paintings": paintings, "ptex": ptex, "puv": puv,
        "people": people, "stands": stands, "carts": carts,
        "title": preset["title"], "world": meta.get("world", ""), "saved": meta.get("saved", ""),
        "points": preset.get("points", []), "pointsTitle": preset.get("points_title", "參考點"),
        "floors": preset.get("floors", []),
    }
    html = (HERE / "viewer.html").read_text(encoding="utf-8")
    three = three_classic()
    data = "window.MODEL=" + json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
    app = (HERE / "viewer.js").read_text(encoding="utf-8")
    for name, part in (("three", three), ("app", app)):
        if "</script" in part.lower():
            raise SystemExit(f"{name} 裡有 </script，會讓網頁壞掉")
    out.parent.mkdir(parents=True, exist_ok=True)
    head, rest = html.split("/*THREE*/")
    mid, rest = rest.split("/*DATA*/")
    mid2, tail = rest.split("/*APP*/")
    out.write_text(head + three + mid + data + mid2 + app + tail, encoding="utf-8")
    print(f"輸出 {out}（{out.stat().st_size / 1e6:.1f} MB）：材質 {len(TEX_LIST)} 張、告示牌 {len(signs)}、旗幟 {len(banners)}、畫 {len(paintings)}、NPC {len(people)}、盔甲座 {len(stands)}")


if __name__ == "__main__":
    main()
