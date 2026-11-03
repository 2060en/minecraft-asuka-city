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

Version numbers (2026-11-03): the game only replaces an imported pack when
its version is higher, so the build bumps the version itself. It hashes what
it assembled (everything but the manifests; images by their pixels, so a
different Pillow does not count as a change) and compares the hash with
addon/pack/release.json. If the content changed, the patch number goes up by
one in both manifests and in release.json; commit them with the change. If
nothing changed, the version stays, so building the same commit again (on
the author's computer too) gives the same version. For a bigger step, write
the new version (e.g. 0.5.0) into resource/manifest.json by hand: the build
then uses it as it is instead of adding one.

Identifier prefix: asukatech (the add-on is called Asuka tech, 2026-11-02).

Rotations: minecraft:transformation turns a block about Y; the Bedrock wiki
uses +90 to turn a north-facing model to face west. All the turns below
follow that; if the game turns them the other way, flip TURN_SIGN.

Geometry: the drafts and tools/preview/ work in what Blockbench shows on
screen. A Bedrock geometry file stores it differently, and Blockbench
converts on import and export (js/formats/bedrock/bedrock.js): x is
mirrored, cube and bone rotations about x and y change sign, and the up and
down faces are turned half way round. The first version copied the drafts
unconverted, so in the game a conveyor curve, since removed, bent the wrong
way and its slope tilted the wrong way (author's test, 2026-11-03). to_bedrock() now
applies Blockbench's export rules. Collision boxes are taken from the
drafts before converting, since they are in world coordinates.
"""
import argparse
import copy
import hashlib
import importlib.util
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
    "coffee_cup": ("外帶咖啡杯", "Takeaway Coffee Cup"),
    "screen": ("小螢幕", "Screen"),
}
GEOS = {   # draft geometry file, identifier in the draft, identifier in the pack
    "door": ("doors/doors.geo.json", "geometry.solid_door", f"geometry.{NS}.door"),
    "trapdoor": ("doors/doors.geo.json", "geometry.solid_trapdoor", f"geometry.{NS}.trapdoor"),
    "coffee_cup": ("coffee_cup/coffee_cup.geo.json", "geometry.coffee_cup", f"geometry.{NS}.coffee_cup"),
    "screen": ("screen_block/screen.geo.json", f"geometry.{NS}.screen", f"geometry.{NS}.screen"),
}
TEXTURES = {   # terrain texture name: draft file
    f"{NS}_door_light_gray": "doors/door_light_gray.png",
    f"{NS}_door_white": "doors/door_white.png",
    f"{NS}_coffee_cup": "coffee_cup/coffee_cup.png",
    f"{NS}_screen": "screen/glow_item_frame.png",      # the first screen picture, black edge
}
SOUNDS = {"door_light_gray": "wood", "door_white": "wood", "trapdoor_light_gray": "wood",
          "trapdoor_white": "wood", "coffee_cup": "wood", "screen": "metal"}


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


# Screen (2026-11-03): a thin panel against the face of the block it was
# placed on, like an item frame; its model faces south. The minecraft:block_face
# state is the face that was clicked, so the panel faces that way. Lying on a
# floor or hanging under a ceiling tilts it about x; if those two come out
# the wrong way round in the game, flip SCREEN_TILT.
SCREEN_TILT = 90
SCREEN_TURN = {"south": [0, 0, 0], "east": [0, 90, 0], "north": [0, 180, 0], "west": [0, 270, 0],
               "up": [-SCREEN_TILT, 0, 0], "down": [SCREEN_TILT, 0, 0]}


def screen():
    perms = [{"condition": cond(**{"minecraft:block_face": f}),
              "components": {"minecraft:transformation": {"rotation": [r[0], TURN_SIGN * r[1], r[2]]}}}
             for f, r in SCREEN_TURN.items()]
    panel = {"origin": [-7, 1, -8], "size": [14, 14, 1]}
    comps = {
        "minecraft:geometry": {"identifier": GEOS["screen"][2]},
        "minecraft:material_instances": {"*": {"texture": f"{NS}_screen", "render_method": "opaque",
                                               "face_dimming": False}},
        "minecraft:destructible_by_mining": {"seconds_to_destroy": 0.5},
        "minecraft:destructible_by_explosion": {"explosion_resistance": 1},
        "minecraft:map_color": "#2f6fb3",
        "minecraft:collision_box": False,
        "minecraft:selection_box": panel,
        "minecraft:light_emission": SCREEN_LIGHT,
        "minecraft:light_dampening": 0,
    }
    traits = {"minecraft:placement_position": {"enabled_states": ["minecraft:block_face"]}}
    return block("screen", {}, traits, comps, perms, category="items")


SCREEN_LIGHT = 6     # how strongly the screen lights itself (and its surroundings); needs a test

# ---------- tableware: custom entities (2026-11-03) ----------
# Like the vanilla cushion: no gravity, no AI, no physics; a small box to hit.
# An item places it (script: addon/pack/behavior/scripts/main.js); hitting it
# picks it up. Removing the add-on removes them (accepted by the author).
TABLEWARE = {   # name: (zh_TW, en_US, hit box width, height)
    "plate": ("白盤子", "White Plate", 0.6, 0.1),
    "bowl": ("白碗", "White Bowl", 0.45, 0.2),
    "cup": ("白杯子", "White Cup", 0.3, 0.3),
    "knife": ("餐刀", "Knife", 0.3, 0.1),
    "fork": ("叉子", "Fork", 0.3, 0.1),
    "spoon": ("湯匙", "Spoon", 0.3, 0.1),
    "chopsticks": ("筷子", "Chopsticks", 0.35, 0.1),
}


def tableware_entity(name):
    _, _, w, h = TABLEWARE[name]
    return {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": f"{NS}:{name}", "is_spawnable": False, "is_summonable": True},
        "components": {
            "minecraft:type_family": {"family": [f"{NS}_tableware", "inanimate"]},
            "minecraft:collision_box": {"width": w, "height": h},
            "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:nameable": {"allow_name_tag_renaming": False},
            "minecraft:conditional_bandwidth_optimization": {},
        }}}


def tableware_client(name):
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": f"{NS}:{name}",
        "materials": {"default": "entity_alphatest"},
        "textures": {"default": f"textures/entity/{NS}/tableware"},
        "geometry": {"default": f"geometry.{NS}.{name}"},
        "render_controllers": ["controller.render.default"],
    }}}


def tableware_item(name):
    return {"format_version": "1.21.90", "minecraft:item": {
        "description": {"identifier": f"{NS}:{name}", "menu_category": {"category": "items"}},
        "components": {
            "minecraft:icon": f"{NS}_{name}",
            "minecraft:display_name": {"value": f"item.{NS}.{name}.name"},
            "minecraft:max_stack_size": 64,
            f"{NS}:tableware": {},
        }}}


# ---------- suitcases: custom entities (2026-11-03, v0.6.0) ----------
# Five cases (addon/drafts/suitcases/), each twice: standing (asukatech:
# suitcase_<name>, a decoration placed like the tableware) and lying on rails
# (asukatech:luggage_cart_<name>, which rides the rails like a minecart). One
# item per case: used on a rail it puts down the cart, on top of anything
# else the standing case. Hitting either picks it up.
SUITCASES = {   # name: (zh_TW, en_US, standing hit box width, height)
    "cabin_navy": ("深藍色登機箱", "Navy Cabin Case", 0.45, 0.85),
    "large_red": ("紅色大行李箱", "Red Large Case", 0.65, 1.1),
    "aluminium": ("鋁製行李箱", "Aluminium Case", 0.6, 1.0),
    "soft_black": ("黑色布面行李箱", "Black Soft Case", 0.6, 1.0),
    "pink": ("粉色行李箱", "Pink Case", 0.6, 1.0),
}


def suitcase_entity(name):
    _, _, w, h = SUITCASES[name]
    return {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": f"{NS}:suitcase_{name}", "is_spawnable": False, "is_summonable": True},
        "components": {
            "minecraft:type_family": {"family": [f"{NS}_suitcase", "inanimate"]},
            "minecraft:collision_box": {"width": w, "height": h},
            "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
            "minecraft:pushable": {"is_pushable": False, "is_pushable_by_piston": False},
            "minecraft:nameable": {"allow_name_tag_renaming": False},
            "minecraft:conditional_bandwidth_optimization": {},
        }}}


def luggage_cart_entity(name):
    """The vanilla minecart's movement (bedrock-samples, minecart.json), no seat."""
    return {"format_version": "1.21.90", "minecraft:entity": {
        "description": {"identifier": f"{NS}:luggage_cart_{name}", "is_spawnable": False, "is_summonable": True},
        "components": {
            "minecraft:type_family": {"family": [f"{NS}_luggage_cart", "minecart", "inanimate"]},
            "minecraft:collision_box": {"width": 0.7, "height": 0.45},
            "minecraft:physics": {},
            "minecraft:rail_movement": {},
            "minecraft:is_stackable": {},
            "minecraft:pushable": {"is_pushable": True, "is_pushable_by_piston": True},
            "minecraft:damage_sensor": {"triggers": [{"cause": "all", "deals_damage": "no"}]},
            "minecraft:nameable": {"allow_name_tag_renaming": False},
            "minecraft:conditional_bandwidth_optimization": {},
        }}}


def suitcase_client(ident, geometry, name):
    return {"format_version": "1.10.0", "minecraft:client_entity": {"description": {
        "identifier": f"{NS}:{ident}",
        "materials": {"default": "entity_alphatest"},
        "textures": {"default": f"textures/entity/{NS}/suitcase_{name}"},
        "geometry": {"default": f"geometry.{NS}.{geometry}"},
        "render_controllers": ["controller.render.default"],
    }}}


def suitcase_item(name):
    return {"format_version": "1.21.90", "minecraft:item": {
        "description": {"identifier": f"{NS}:suitcase_{name}", "menu_category": {"category": "items"}},
        "components": {
            "minecraft:icon": f"{NS}_suitcase_{name}",
            "minecraft:display_name": {"value": f"item.{NS}.suitcase_{name}.name"},
            "minecraft:max_stack_size": 64,
            f"{NS}:suitcase": {},
        }}}


def load_draft(path):
    """Import a draft's build.py whose work sits behind `if __name__ == "__main__"`."""
    spec = importlib.util.spec_from_file_location(f"draft_{Path(path).parent.name}", DRAFTS / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        "coffee_cup": coffee_cup(),
        "screen": screen(),
    }
    for old in (bp / "blocks").glob("*.json"):
        old.unlink()
    for name, data in blocks.items():
        write_json(bp / "blocks" / f"{name}.json", data)
    for n in range(2, 5):
        write_json(bp / "loot_tables" / NS / f"coffee_cup_{n}.json", cup_loot(n))
    for folder in (bp / "entities", bp / "items", rp / "entity"):
        for old in folder.glob("*.json"):
            old.unlink()
    for name in TABLEWARE:
        write_json(bp / "entities" / f"{name}.json", tableware_entity(name))
        write_json(bp / "items" / f"{name}.json", tableware_item(name))
        write_json(rp / "entity" / f"{name}.entity.json", tableware_client(name))
    for name in SUITCASES:
        write_json(bp / "entities" / f"suitcase_{name}.json", suitcase_entity(name))
        write_json(bp / "entities" / f"luggage_cart_{name}.json", luggage_cart_entity(name))
        write_json(bp / "items" / f"suitcase_{name}.json", suitcase_item(name))
        write_json(rp / "entity" / f"suitcase_{name}.entity.json",
                   suitcase_client(f"suitcase_{name}", f"suitcase_{name}", name))
        write_json(rp / "entity" / f"luggage_cart_{name}.entity.json",
                   suitcase_client(f"luggage_cart_{name}", f"luggage_cart_{name}", name))
    icons = {f"{NS}_{n}": f"textures/items/{NS}/{n}" for n in TABLEWARE}
    icons.update({f"{NS}_suitcase_{n}": f"textures/items/{NS}/suitcase_{n}" for n in SUITCASES})
    write_json(rp / "textures" / "item_texture.json", {
        "resource_pack_name": NS, "texture_name": "atlas.items",
        "texture_data": {k: {"textures": v} for k, v in icons.items()},
    })
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
        names += [f"item.{NS}.{n}.name={v[i]}" for n, v in TABLEWARE.items()]
        names += [f"entity.{NS}:{n}.name={v[i]}" for n, v in TABLEWARE.items()]
        names += [f"item.{NS}.suitcase_{n}.name={v[i]}" for n, v in SUITCASES.items()]
        names += [f"entity.{NS}:suitcase_{n}.name={v[i]}" for n, v in SUITCASES.items()]
        names += [f"entity.{NS}:luggage_cart_{n}.name={v[i]}" for n, v in SUITCASES.items()]
        names += load_draft("drinks/build.py").lang_lines(lang)      # potions become drinks
        path.write_text("\n".join(head + names) + "\n", encoding="utf-8")
    print(f"generated {len(blocks)} blocks")


# ---------- version ----------
RELEASE = HERE / "release.json"
MANIFESTS = (HERE / "resource" / "manifest.json", HERE / "behavior" / "manifest.json")


def content_hash(folders):
    h = hashlib.sha256()
    for folder in folders:
        for f in sorted(folder.rglob("*")):
            if not f.is_file() or f.name == "manifest.json":
                continue
            h.update(f"{folder.name}/{f.relative_to(folder).as_posix()}\n".encode())
            if f.suffix == ".png":
                with Image.open(f) as img:
                    h.update(f"{img.mode} {img.size}\n".encode())
                    h.update(img.tobytes())
            else:
                h.update(f.read_bytes())
    return h.hexdigest()


def set_version(manifest, version, rp_uuid):
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["header"]["version"] = version
    for module in data["modules"]:
        module["version"] = version
    for dep in data.get("dependencies", []):
        if dep.get("uuid") == rp_uuid:
            dep["version"] = version
    write_json(manifest, data)


def update_version(folders):
    """Bump the patch number when the assembled content changed; returns the version."""
    digest = content_hash(folders)
    release = json.loads(RELEASE.read_text(encoding="utf-8"))
    rp = json.loads(MANIFESTS[0].read_text(encoding="utf-8"))["header"]
    version = rp["version"]
    if digest != release["content_hash"]:
        if version == release["version"]:
            version = version[:2] + [version[2] + 1]
        for manifest in MANIFESTS:
            set_version(manifest, version, rp["uuid"])
        write_json(RELEASE, {"version": version, "content_hash": digest})
        print(f"content changed: version {'.'.join(map(str, version))} (commit the manifests and release.json)")
    else:
        print(f"content unchanged: version stays {'.'.join(map(str, version))}")
    for manifest, folder in zip(MANIFESTS, folders):
        shutil.copy(manifest, folder / "manifest.json")
    return version


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
    # second batch (2026-11-03)
    "suitcase/chest.png": "textures/entity/chest/normal.png",
    "suitcase/chest_double.png": "textures/entity/chest/double_normal.png",
    "drawer/shulker_silver.png": "textures/entity/shulker/shulker_silver.png",
    "drawer/shulker_top_silver.png": "textures/blocks/shulker_top_silver.png",
    "cup/sea_pickle.png": "textures/blocks/sea_pickle.png",
    "cup/cup_item.png": "textures/items/sea_pickle.png",
    "tableware/tableware.png": f"textures/entity/{NS}/tableware.png",
    **{f"tableware/icons/{n}.png": f"textures/items/{NS}/{n}.png" for n in TABLEWARE},
    # v0.6.0: the coffee stand and the suitcases
    "coffee_machine/brewing_stand.png": "textures/blocks/brewing_stand.png",
    "coffee_machine/brewing_stand_base.png": "textures/blocks/brewing_stand_base.png",
    "coffee_machine/brewing_stand_item.png": "textures/items/brewing_stand.png",
    **{f"suitcases/{n}.png": f"textures/entity/{NS}/suitcase_{n}.png" for n in SUITCASES},
    **{f"suitcases/icons/{n}.png": f"textures/items/{NS}/suitcase_{n}.png" for n in SUITCASES},
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

    # drinks: the potion icons
    for f in (DRAFTS / "drinks" / "icons").glob("*.png"):
        shutil.copy(f, rp_out / "textures" / "items" / f.name)
    # retextures made from the vanilla files (cushion, flower pot, decorated pot,
    # wither skull, pale oak shelf, milk carton): drawn at build time
    load_draft("props/build.py").make_all(rp_out)
    # entity models: tableware and suitcases
    for draft, out in (("tableware/tableware.geo.json", "tableware"), ("suitcases/suitcases.geo.json", "suitcases")):
        data = json.loads((DRAFTS / draft).read_text(encoding="utf-8"))
        for g in data["minecraft:geometry"]:     # so a tall case is not culled at the screen edge
            g["description"].update({"visible_bounds_width": 2, "visible_bounds_height": 2,
                                     "visible_bounds_offset": [0, 0.75, 0]})
        write_json(rp_out / "models" / "entity" / f"{NS}_{out}.geo.json",
                   {"format_version": data["format_version"],
                    "minecraft:geometry": [to_bedrock(g) for g in data["minecraft:geometry"]]})

    update_version((rp_out, bp_out))
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
