"""Build the Asuka tech add-on: a resource pack and a behaviour pack.

Run from the repository root:
    python3 addon/pack/build.py [--vanilla DIR]

Two jobs:

1. Generate the block definitions (addon/pack/behavior/blocks/*.json) and the
   resource pack's block lists (terrain_texture.json, blocks.json, names in
   texts/). They are generated because a block's permutations multiply out
   (a door: 4 directions x upper/lower x open x hinge), which is easy to get
   wrong by hand. The generated files are committed, so they can be read.
2. Assemble addon/build/Asuka tech RP/ and Asuka tech BP/ from addon/pack/,
   the finished drafts in addon/drafts/ and the advertisement textures, and
   zip both into addon/build/Asuka tech.mcaddon. kz.png needs the vanilla
   paintings that have no advertisement, so the vanilla kz.png is read from
   --vanilla DIR (a textures/painting folder) or downloaded from
   https://github.com/Mojang/bedrock-samples into addon/build/vanilla/.
   addon/build/ is not committed: no vanilla image in the repository.

Identifier prefix: asukatech (the add-on is called Asuka tech, 2026-11-02).

Rotations: minecraft:transformation turns a block about Y; the Bedrock wiki
uses +90 to turn a north-facing model to face west. All the turns below
follow that; if the game turns them the other way, flip TURN_SIGN.

Geometry: the drafts and tools/preview/ work in what Blockbench shows on
screen. A Bedrock geometry file stores it differently, and Blockbench
converts on import and export (js/formats/bedrock/bedrock.js): x is
mirrored, cube and bone rotations about x and y change sign, and the up and
down faces are turned half way round. The first version copied the drafts
unconverted, so in the game the conveyor's curve bent the wrong way and its
slope tilted the wrong way (author's test, 2026-11-03). to_bedrock() now
applies Blockbench's export rules. Collision boxes are taken from the
drafts before converting, since they are in world coordinates.
"""
import argparse
import copy
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DRAFTS = ROOT / "addon" / "drafts"
BUILD = ROOT / "addon" / "build"
NS = "asukatech"
TURN_SIGN = 1                 # flip to -1 if every rotated block turns the wrong way
BLOCK_FORMAT = "1.21.90"      # custom components v2 need 1.21.90 or later

# ---------- the custom blocks ----------
# name: (zh_TW, en_US)
NAMES = {
    "door_light_gray": ("淺灰色門", "Light Gray Door"),
    "door_white": ("白色門", "White Door"),
    "trapdoor_light_gray": ("淺灰色地板門", "Light Gray Trapdoor"),
    "trapdoor_white": ("白色地板門", "White Trapdoor"),
    "conveyor": ("傳送履帶機身", "Conveyor Body"),
    "coffee_cup": ("外帶咖啡杯", "Takeaway Coffee Cup"),
}
GEOS = {   # draft geometry file, identifier in the draft, identifier in the pack
    "door": ("doors/doors.geo.json", "geometry.solid_door", f"geometry.{NS}.door"),
    "trapdoor": ("doors/doors.geo.json", "geometry.solid_trapdoor", f"geometry.{NS}.trapdoor"),
    "conveyor": ("conveyor/conveyor_body.geo.json", "geometry.conveyor_body", f"geometry.{NS}.conveyor"),
    "coffee_cup": ("coffee_cup/coffee_cup.geo.json", "geometry.coffee_cup", f"geometry.{NS}.coffee_cup"),
}
TEXTURES = {   # terrain texture name: draft file
    f"{NS}_door_light_gray": "doors/door_light_gray.png",
    f"{NS}_door_white": "doors/door_white.png",
    f"{NS}_conveyor": "conveyor/conveyor.png",
    f"{NS}_coffee_cup": "coffee_cup/coffee_cup.png",
}
SOUNDS = {"door_light_gray": "wood", "door_white": "wood", "trapdoor_light_gray": "wood",
          "trapdoor_white": "wood", "conveyor": "metal", "coffee_cup": "wood"}


def to_bedrock(geo):
    """Blockbench's export rules (compileCube, compileGroup): what Blockbench
    shows, as a Bedrock geometry file stores it."""
    g = copy.deepcopy(geo)
    for bone in g["bones"]:
        if "pivot" in bone:
            bone["pivot"][0] = -bone["pivot"][0]
        if "rotation" in bone:
            bone["rotation"][0], bone["rotation"][1] = -bone["rotation"][0], -bone["rotation"][1]
        for c in bone.get("cubes", []):
            c["origin"][0] = -(c["origin"][0] + c["size"][0])
            if "pivot" in c:
                c["pivot"][0] = -c["pivot"][0]
            if "rotation" in c:
                c["rotation"][0], c["rotation"][1] = -c["rotation"][0], -c["rotation"][1]
            uv = c.get("uv")
            if isinstance(uv, dict):
                for face in ("up", "down"):
                    f = uv.get(face)
                    if f and "uv_size" in f:
                        f["uv"] = [f["uv"][0] + f["uv_size"][0], f["uv"][1] + f["uv_size"][1]]
                        f["uv_size"] = [-f["uv_size"][0], -f["uv_size"][1]]
    return g


def load_geo(key):
    path, ident, _ = GEOS[key]
    data = json.loads((DRAFTS / path).read_text(encoding="utf-8"))
    return next(g for g in data["minecraft:geometry"] if g["description"]["identifier"] == ident)


def bone_box(geo, bone):
    """Bounding box of a bone's cubes, clamped to the block, as a Bedrock box."""
    cubes = next(b for b in geo["bones"] if b["name"] == bone)["cubes"]
    lo = [min(c["origin"][i] for c in cubes) for i in range(3)]
    hi = [max(c["origin"][i] + c["size"][i] for c in cubes) for i in range(3)]
    lo = [max(-8, lo[0]), max(0, lo[1]), max(-8, lo[2])]
    hi = [min(8, hi[0]), min(16, hi[1]), min(8, hi[2])]
    box = {"origin": [round(v, 3) for v in lo], "size": [round(h - l, 3) for h, l in zip(hi, lo)]}
    return box


def geometry(key, visible):
    geo = load_geo(key)
    return {"identifier": GEOS[key][2], "bone_visibility": {b["name"]: b["name"] in visible for b in geo["bones"]}}


def turn(degrees):
    return {"minecraft:transformation": {"rotation": [0, TURN_SIGN * degrees, 0]}}


def cond(**states):
    parts = []
    for k, v in states.items():
        name = k if ":" in k else f"{NS}:{k}"
        if k == "cardinal":
            name = "minecraft:cardinal_direction"
        elif k == "half":
            name = "minecraft:vertical_half"
        if isinstance(v, bool):
            parts.append(f"q.block_state('{name}') == {'true' if v else 'false'}")
        elif isinstance(v, str):
            parts.append(f"q.block_state('{name}') == '{v}'")
        else:
            parts.append(f"q.block_state('{name}') == {v}")
    return " && ".join(parts)


def block(name, states, traits, components, permutations, category="construction"):
    desc = {"identifier": f"{NS}:{name}", "menu_category": {"category": category}}
    if states:
        desc["states"] = states
    if traits:
        desc["traits"] = traits
    return {"format_version": BLOCK_FORMAT,
            "minecraft:block": {"description": desc, "components": components, "permutations": permutations}}


def common(texture, seconds, resistance, color, render="alpha_test"):
    return {
        "minecraft:material_instances": {"*": {"texture": texture, "render_method": render}},
        "minecraft:destructible_by_mining": {"seconds_to_destroy": seconds},
        "minecraft:destructible_by_explosion": {"explosion_resistance": resistance},
        "minecraft:map_color": color,
    }


# Door: the model's panel lies on the north edge with the hinge at the west
# end and opens toward the south. A player facing south stands north of the
# block, so the panel is on the edge nearest the player, as in vanilla.
DOOR_TURN = {"south": 0, "east": 90, "north": 180, "west": 270}
# Trapdoor: open, it stands against the north edge, the far edge for a
# player facing north (the wall they placed it on).
TRAPDOOR_TURN = {"north": 0, "west": 90, "south": 180, "east": 270}
CUP_TURN = DOOR_TURN


def door(color):
    geo = load_geo("door")
    perms = [{"condition": cond(cardinal=d), "components": turn(a)} for d, a in DOOR_TURN.items()]
    for upper in (False, True):
        for open_ in (False, True):
            for right in (False, True):
                bone = f"{'upper' if upper else 'lower'}_{'open' if open_ else 'closed'}_{'r' if right else 'l'}"
                box = bone_box(geo, bone)
                comps = {"minecraft:geometry": geometry("door", {bone}),
                         "minecraft:collision_box": box, "minecraft:selection_box": box}
                if upper:
                    comps["minecraft:loot"] = "loot_tables/empty.json"   # the lower half drops the door
                perms.append({"condition": cond(upper=upper, open=open_, hinge_right=right), "components": comps})
    comps = {
        "minecraft:geometry": geometry("door", {"lower_closed_l"}),
        **common(f"{NS}_door_{color}", 3, 3, "#d8d8d8" if color == "light_gray" else "#f4f4f4"),
        "minecraft:collision_box": bone_box(geo, "lower_closed_l"),
        "minecraft:selection_box": bone_box(geo, "lower_closed_l"),
        "minecraft:light_dampening": 0,
        "minecraft:placement_filter": {"conditions": [{"allowed_faces": ["up"]}]},
        "minecraft:tick": {"interval_range": [5, 5], "looping": True},
        f"{NS}:door": {},
    }
    states = {f"{NS}:upper": [False, True], f"{NS}:open": [False, True],
              f"{NS}:hinge_right": [False, True], f"{NS}:powered": [False, True]}
    traits = {"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 0}}
    return block(f"door_{color}", states, traits, comps, perms)


def trapdoor(color):
    geo = load_geo("trapdoor")
    perms = [{"condition": cond(cardinal=d), "components": turn(a)} for d, a in TRAPDOOR_TURN.items()]
    for half in ("bottom", "top"):
        for open_ in (False, True):
            bone = "open" if open_ else half
            box = bone_box(geo, bone)
            perms.append({"condition": cond(half=half, open=open_),
                          "components": {"minecraft:geometry": geometry("trapdoor", {bone}),
                                         "minecraft:collision_box": box, "minecraft:selection_box": box}})
    comps = {
        "minecraft:geometry": geometry("trapdoor", {"bottom"}),
        **common(f"{NS}_door_{color}", 3, 3, "#d8d8d8" if color == "light_gray" else "#f4f4f4"),
        "minecraft:collision_box": bone_box(geo, "bottom"),
        "minecraft:selection_box": bone_box(geo, "bottom"),
        "minecraft:light_dampening": 0,
        "minecraft:tick": {"interval_range": [5, 5], "looping": True},
        f"{NS}:trapdoor": {},
    }
    states = {f"{NS}:open": [False, True], f"{NS}:powered": [False, True]}
    traits = {"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 0},
              "minecraft:placement_position": {"enabled_states": ["minecraft:vertical_half"]}}
    return block(f"trapdoor_{color}", states, traits, comps, perms)


def conveyor():
    """The conveyor body. A vanilla rail sits on top; the script copies the
    rail's shape into shape (0 no rail, 1 straight, 2 curve, 3 slope) and turn
    (quarter turns), and sets cap_s/cap_n/cap_e when a slope rises into this
    block's rail from that side (in the model's own frame), so this body
    draws the top of that slope. Powered and plain rails look the same
    (decided 2026-11-02)."""
    shapes = {0: set(), 1: {"belt_straight"}, 2: {"belt_curve"}, 3: {"belt_slope"}}
    perms = [{"condition": cond(turn=k), "components": turn(90 * k)} for k in range(4)]
    for shape, bones in shapes.items():
        for s in (False, True):
            for n in (False, True):
                for e in (False, True):
                    visible = {"body"} | bones | {b for b, on in (("cap_s", s), ("cap_n", n), ("cap_e", e)) if on}
                    perms.append({"condition": cond(shape=shape, cap_s=s, cap_n=n, cap_e=e),
                                  "components": {"minecraft:geometry": geometry("conveyor", visible)}})
    full = {"origin": [-8, 0, -8], "size": [16, 16, 16]}
    comps = {
        "minecraft:geometry": geometry("conveyor", {"body"}),
        **common(f"{NS}_conveyor", 5, 6, "#6e7378"),
        "minecraft:collision_box": full,
        "minecraft:selection_box": full,
        "minecraft:tick": {"interval_range": [10, 10], "looping": True},
        f"{NS}:conveyor": {},
    }
    states = {f"{NS}:shape": [0, 1, 2, 3], f"{NS}:turn": [0, 1, 2, 3],
              f"{NS}:cap_s": [False, True], f"{NS}:cap_n": [False, True], f"{NS}:cap_e": [False, True]}
    return block("conveyor", states, None, comps, perms)


def coffee_cup():
    geo = load_geo("coffee_cup")
    perms = [{"condition": cond(cardinal=d), "components": turn(a)} for d, a in CUP_TURN.items()]
    for n in range(1, 5):
        box = bone_box(geo, f"count_{n}")
        comps = {"minecraft:geometry": geometry("coffee_cup", {f"count_{n}"}),
                 "minecraft:collision_box": box, "minecraft:selection_box": box}
        if n > 1:
            comps["minecraft:loot"] = f"loot_tables/{NS}/coffee_cup_{n}.json"
        perms.append({"condition": cond(count=n), "components": comps})
    box = bone_box(geo, "count_1")
    comps = {
        "minecraft:geometry": geometry("coffee_cup", {"count_1"}),
        **common(f"{NS}_coffee_cup", 0, 0, "#f2efe8"),
        "minecraft:collision_box": box,
        "minecraft:selection_box": box,
        "minecraft:light_dampening": 0,
        "minecraft:placement_filter": {"conditions": [{"allowed_faces": ["up"]}]},
        f"{NS}:coffee_cup": {},
    }
    states = {f"{NS}:count": [1, 2, 3, 4]}
    traits = {"minecraft:placement_direction": {"enabled_states": ["minecraft:cardinal_direction"], "y_rotation_offset": 0}}
    return block("coffee_cup", states, traits, comps, perms, category="items")


def cup_loot(n):
    return {"pools": [{"rolls": 1, "entries": [{"type": "item", "name": f"{NS}:coffee_cup",
                                                 "functions": [{"function": "set_count", "count": n}]}]}]}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate():
    bp, rp = HERE / "behavior", HERE / "resource"
    blocks = {
        "door_light_gray": door("light_gray"), "door_white": door("white"),
        "trapdoor_light_gray": trapdoor("light_gray"), "trapdoor_white": trapdoor("white"),
        "conveyor": conveyor(), "coffee_cup": coffee_cup(),
    }
    for old in (bp / "blocks").glob("*.json"):
        old.unlink()
    for name, data in blocks.items():
        write_json(bp / "blocks" / f"{name}.json", data)
    for n in range(2, 5):
        write_json(bp / "loot_tables" / NS / f"coffee_cup_{n}.json", cup_loot(n))
    write_json(rp / "textures" / "terrain_texture.json", {
        "resource_pack_name": NS, "texture_name": "atlas.terrain", "padding": 8, "num_mip_levels": 4,
        "texture_data": {k: {"textures": f"textures/blocks/{NS}/{Path(v).stem}"} for k, v in TEXTURES.items()},
    })
    write_json(rp / "blocks.json", {"format_version": "1.21.40",
                                     **{f"{NS}:{n}": {"sound": SOUNDS[n]} for n in NAMES}})
    for lang, i in (("zh_TW", 0), ("en_US", 1)):
        path = rp / "texts" / f"{lang}.lang"
        head = [l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("pack.")]
        names = [f"tile.{NS}:{n}.name={v[i]}" for n, v in NAMES.items()]
        path.write_text("\n".join(head + names) + "\n", encoding="utf-8")
    print(f"generated {len(blocks)} blocks")


# ---------- assemble the packs ----------
ADS = DRAFTS / "ads"
RETEXTURES = {   # draft file: path in the resource pack
    "white_frame/itemframe_background.png": "textures/blocks/itemframe_background.png",
    "screen/glow_item_frame.png": "textures/blocks/glow_item_frame.png",
    "locker/shulker_white.png": "textures/entity/shulker/shulker_white.png",
    "locker/shulker_top_white.png": "textures/blocks/shulker_top_white.png",
    "hopper/hopper_inside.png": "textures/blocks/hopper_inside.png",
    "hopper/hopper_outside.png": "textures/blocks/hopper_outside.png",
    "hopper/hopper_top.png": "textures/blocks/hopper_top.png",
}
VANILLA_KZ = "https://raw.githubusercontent.com/Mojang/bedrock-samples/main/resource_pack/textures/painting/kz.png"


def vanilla_kz(folder):
    if folder:
        return Image.open(Path(folder) / "kz.png")
    cache = BUILD / "vanilla" / "kz.png"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(VANILLA_KZ, cache)
    return Image.open(cache)


def assemble(vanilla_folder):
    rp_out, bp_out = BUILD / "Asuka tech RP", BUILD / "Asuka tech BP"
    for out in (rp_out, bp_out):
        shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(HERE / "resource", rp_out)
    shutil.copytree(HERE / "behavior", bp_out)

    for key, (path, ident, new) in GEOS.items():
        data = json.loads((DRAFTS / path).read_text(encoding="utf-8"))
        geo = next(g for g in data["minecraft:geometry"] if g["description"]["identifier"] == ident)
        geo = to_bedrock(geo)
        geo["description"]["identifier"] = new
        write_json(rp_out / "models" / "blocks" / f"{NS}_{key}.geo.json",
                   {"format_version": data["format_version"], "minecraft:geometry": [geo]})
    for name, path in TEXTURES.items():
        dest = rp_out / "textures" / "blocks" / NS / f"{Path(path).stem}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DRAFTS / path, dest)
    for out in (rp_out, bp_out):
        shutil.copy(HERE / "pack_icon.png", out / "pack_icon.png")
    for src, dest in RETEXTURES.items():
        (rp_out / dest).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DRAFTS / src, rp_out / dest)

    # paintings: the advertisements and the laptop over the vanilla kz.png
    overlay = Image.open(ADS / "kz_overlay.png").convert("RGBA")
    kz = vanilla_kz(vanilla_folder).convert("RGBA").resize(overlay.size, Image.NEAREST)
    kz.alpha_composite(overlay)
    (rp_out / "textures" / "painting").mkdir(parents=True, exist_ok=True)
    kz.save(rp_out / "textures" / "painting" / "kz.png")
    for f in (ADS / "painting").glob("*.png"):
        shutil.copy(f, rp_out / "textures" / "painting" / f.name)

    mcaddon = BUILD / "Asuka tech.mcaddon"
    with zipfile.ZipFile(mcaddon, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in (rp_out, bp_out):
            for f in sorted(folder.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(BUILD))
    print(f"wrote {rp_out.relative_to(ROOT)}/, {bp_out.relative_to(ROOT)}/ and {mcaddon.relative_to(ROOT)} "
          f"({mcaddon.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla", help="folder with the vanilla textures/painting files")
    args = parser.parse_args()
    generate()
    assemble(args.vanilla)
