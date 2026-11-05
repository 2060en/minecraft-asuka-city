"""組 Asuka toolkit（只有腳本的行為包）。

在 repo 根目錄執行：
    python tools/asuka-toolkit/build.py                          組出 addon/build/Asuka toolkit v<版本>.mcpack
    python tools/asuka-toolkit/build.py --dev [--mojang DIR]     開發版，直接放進遊戲的開發用資料夾

版本號（和 Asuka tech、Rail to Belt 相同）：同一個包要用新的版本號，遊戲才會當成新版匯入。
這裡比較 manifest 以外的檔案內容（文字檔先統一換行，因為 Windows 上的 git 會寫成 CRLF）和
release.json 記的雜湊，內容有變就把最後一位加一；要跳大版本就手動改 behavior_pack/manifest.json。

開發版：內容相同，只差 UUID、名稱和固定的版本號，所以不會影響匯入正式版的世界，也不動正式版的
版本號與 release.json。同一個世界不要同時啟用兩個：備用指令 /asuka:menu 這些名稱是一樣的。
"""
import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACK = HERE / "behavior_pack"
MANIFEST = PACK / "manifest.json"
RELEASE = HERE / "release.json"
BUILD = ROOT / "addon" / "build"
FILE_NAME = "Asuka toolkit"

DEV_NAME = "Asuka toolkit DEV"
DEV_FOLDER = "Asuka toolkit DEV"
DEV_VERSION = [0, 0, 1]
DEV_UUIDS = {   # 正式版的 UUID：開發版的
    "257e1696-a5ae-4568-a53a-1acebef22fce": "c1d1d4a5-5e0b-4c9e-8a57-6f3b3f1a7e21",   # 行為包
    "27e9b1e4-466f-436d-ba3c-678f5d6d0969": "4b7f0c62-93d8-4a16-b2a4-0d8e5c7f1b39",   # 腳本模組
}
# GDK 版放匯入的包的地方；Asuka tech 的開發版已確認行為包清單看得到（作者截圖，2026-11-04）
GAME_FOLDER = Path(os.environ.get("APPDATA", "")) / "Minecraft Bedrock" / "Users" / "Shared" / "games" / "com.mojang"


def pack_files():
    files = (f for f in PACK.rglob("*") if f.is_file())
    return sorted(files, key=lambda f: f.relative_to(PACK).as_posix())


def content_hash():
    h = hashlib.sha256()
    for f in pack_files():
        if f == MANIFEST:
            continue
        h.update(f"{f.relative_to(PACK).as_posix()}\n".encode())
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def update_version():
    """內容有變就把最後一位加一，回傳版本號。"""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    version = manifest["header"]["version"]
    digest = content_hash()
    release = json.loads(RELEASE.read_text(encoding="utf-8")) if RELEASE.exists() else {"version": version, "content_hash": digest}
    if digest != release["content_hash"]:
        if version == release["version"]:
            version = version[:2] + [version[2] + 1]
        print(f"content changed: version {'.'.join(map(str, version))} (commit manifest.json and release.json)")
    else:
        print(f"content unchanged: version stays {'.'.join(map(str, version))}")
    manifest["header"]["version"] = version
    for module in manifest["modules"]:
        module["version"] = version
    write_json(MANIFEST, manifest)
    write_json(RELEASE, {"version": version, "content_hash": digest})
    return version


def package():
    version = ".".join(map(str, update_version()))
    BUILD.mkdir(parents=True, exist_ok=True)
    for old in BUILD.glob(f"{FILE_NAME} v*.mcpack"):    # 只留最新的一個，才不會裝錯
        old.unlink()
    out = BUILD / f"{FILE_NAME} v{version}.mcpack"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pack_files():
            info = zipfile.ZipInfo(f.relative_to(PACK).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    print(f"wrote {out.relative_to(ROOT)}")


def game_folder(given):
    folder = Path(given) if given else GAME_FOLDER
    if not (folder / "development_behavior_packs").is_dir():
        raise SystemExit(f"no development_behavior_packs in {folder}; say where with --mojang DIR")
    return folder


def install_dev(folder):
    """先在 addon/build 組好再複製過去：遊戲不會讀到組到一半的檔案。只取代這一個資料夾。"""
    staging = BUILD / "dev" / DEV_FOLDER
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(PACK, staging)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["header"].update(name=DEV_NAME, uuid=DEV_UUIDS[manifest["header"]["uuid"]], version=DEV_VERSION)
    for module in manifest["modules"]:
        module.update(uuid=DEV_UUIDS[module["uuid"]], version=DEV_VERSION)
    write_json(staging / "manifest.json", manifest)
    dest = folder / "development_behavior_packs" / DEV_FOLDER
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(staging, dest)
    print(f"wrote {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="組開發版，放進遊戲的開發用資料夾")
    parser.add_argument("--mojang", help="和 --dev 一起用：遊戲的 com.mojang 資料夾，不是平常那個時才要指定")
    args = parser.parse_args()
    if args.dev:
        install_dev(game_folder(args.mojang))
    else:
        package()
