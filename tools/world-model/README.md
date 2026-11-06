# 區域 3D 模型

把世界裡一個範圍（例如一棟建築）的方塊讀出來，做成可以在瀏覽器裡旋轉、縮放、逐層切開的 3D 模型，另外輸出各樓層的平面圖。用來對著實際空間討論配置，例如「出境大廳該有哪些設施」。

第一次用在 AKQ 國際航廈（2026-11-06），範圍設定在 `presets/akq.json`。

## 安全

只讀不寫，和轉換程式的掃描（`tools/converter/scan.py`）用同一套保護：

- 遊戲開著時拒絕讀遊戲資料夾裡的世界，請先關遊戲
- 世界本體絕對不開：先把 `db` 複製到暫存資料夾，只開那份副本，讀完就刪掉
- 讀完核對世界本體的檔案清單、大小與修改時間，有變動會用★提醒

## 第一次使用

需要 Python 3.12、Node.js、git。在 repo 根目錄執行：

```bash
python -m venv tools/world-model/.venv
tools/world-model/.venv/Scripts/python.exe -m pip install -r tools/world-model/requirements.txt
cd tools/preview && npm install && cd ../..
```

- Python 套件：`amulet-leveldb`（讀基岩版的 LevelDB 資料庫）、`numpy`、`Pillow`（處理圖片）
- `tools/preview` 裡的 three.js（3D 繪圖）會整個包進網頁，所以網頁不用網路；playwright 用來截圖，它自己的瀏覽器沒下載時會改用電腦裡的 Chrome 或 Edge
- 原版材質：第一次做模型時，自動從 Mojang 官方的 [bedrock-samples](https://github.com/Mojang/bedrock-samples) 只下載方塊、畫、旗幟圖樣的材質（約 15 MB），放在 `.cache/`，不進 repo
- 世界掛的 Asuka tech 資源包：依照世界的 `world_resource_packs.json` 到 `addon/build/` 裡找同一個編號的包，所以要先組過包（`addon/pack/build.py`）；找不到時只用原版材質，置物櫃、廣告畫會變回原版的樣子

## 步驟

輸出建議放在 repo 外面，例如 `addon_dev\akq_terminal_model\`（模型網頁約 3 MB，平面圖每張約 1 MB）。

```bash
# 1. 讀出範圍內的方塊、告示牌、旗幟、畫、NPC、盔甲座（遊戲要關著）
tools/world-model/.venv/Scripts/python.exe tools/world-model/extract.py CX198-test --preset akq --out <資料夾>

# 2. 做成 3D 模型網頁
tools/world-model/.venv/Scripts/python.exe tools/world-model/build.py <資料夾> --preset akq --out <輸出>/模型.html

# 3. 各樓層的平面圖
tools/world-model/.venv/Scripts/python.exe tools/world-model/plans.py <資料夾> <輸出>/模型.html --preset akq --out <輸出>/平面圖

# 改了程式之後：小測試與網頁操作檢查
tools/world-model/.venv/Scripts/python.exe tools/world-model/test_world_model.py
node tools/world-model/check_viewer.mjs <輸出>/模型.html
```

世界可以給名稱（`levelname.txt`，要完全相同，例如 `CX198`、`CX198-test`）或資料夾路徑。不想寫範圍設定時，`extract.py` 也可以直接給 `--box X0 X1 Y0 Y1 Z0 Z1`，但 `build.py` 還是要一個設定檔（至少要有 `title`）。

## 範圍設定（presets/）

```json
{
 "title": "AKQ 國際航廈",
 "box": [686, 840, 62, 95, 205, 500],
 "floors": [{"name": "出境大廳", "floor": 77, "lo": 76, "hi": 81, "note": "…"}],
 "points_title": "參考點（Ian 2026-11-06 的截圖位置）",
 "points": [{"name": "1 置物櫃與外幣兌換", "p": [789, 78, 453], "yaw": -135, "pitch": 5}]
}
```

- `box`：X0 X1 Y0 Y1 Z0 Z1（含兩端）
- `floors`：網頁的樓層按鈕與平面圖。`floor` 是地板高度，`lo`～`hi` 是要顯示的高度；天花板低於上一層地板時（例如 AKQ 的候機區），`hi` 要切在天花板底下
- `points`：參考點，點一下就站到那裡、面向那個方向。`p` 是遊戲左上角「位置」顯示的座標，`yaw`、`pitch` 用 Minecraft 的定義（yaw 0 朝南、90 朝西、180 朝北、-90 朝東；pitch 正數往下看）

## 網頁的操作

- **環繞**：左鍵拖曳旋轉、右鍵拖曳平移、滾輪縮放，W A S D 移動中心點
- **漫遊**：左鍵拖曳轉頭，W A S D 前後左右，空白鍵或 E 上升、Q 下降，滾輪調速度
- **平面圖**：正上方、北方在上，拖曳平移、滾輪縮放
- 樓層按鈕與兩條滑桿決定顯示的高度；玻璃、告示牌文字、畫、NPC 與盔甲座、座標尺可以分別關掉
- 游標指著方塊時，底下顯示座標、方塊名稱和告示牌文字；按住 Shift 點方塊加標記，可以複製標記的座標
- 給截圖程式用：`window.MODEL_VIEW.goWalk(x, y, z, yaw, pitch)` 直接移動視角

## 和遊戲不一樣的地方

外觀是近似的，夠討論配置用：

- 沒有光影，只有每個面固定的明暗和角落陰影
- 樓梯只做直的（轉角當成直的）；柵欄、玻璃片、鐵欄杆依旁邊的方塊自動接起來；牆用存檔裡記的連接方向
- 直立告示牌、旗幟只轉成東西南北四個方向；旗幟的圖樣照存檔裡的底色與圖樣疊出來
- 界伏蚌盒照 Asuka tech 畫成置物櫃，門的朝向從方塊實體讀
- NPC 是簡單的人形；盔甲座只畫支架、頭盔、護腿、手上拿的盾牌（深色板子）和地毯；物品框裡的東西不畫
- 自製的輸送帶（`asukatech:conveyor`）畫成薄板；其他自製方塊找不到材質時是洋紅色

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `extract.py` | 讀世界副本，輸出 `region.npz`（方塊編號，Y、Z、X 順序）、`meta.json`（調色盤、原點、世界名稱與存檔時間、資源包編號）、`block_entities.json`、`entities.json` |
| `build.py` | 材質拼圖、形狀、告示牌、旗幟、畫，和 three.js、`viewer.html`、`viewer.js` 組成一個網頁 |
| `viewer.html`、`viewer.js` | 網頁本體：網格在瀏覽器裡建（每一層分開，切層時不用重建） |
| `plans.py` | 平面圖：呼叫 `shot.mjs` 截正投影，再加標題、參考點、告示牌文字 |
| `shot.mjs` | 用無畫面瀏覽器照一連串視角截圖（說明在檔案開頭） |
| `check_viewer.mjs`、`test_world_model.py` | 網頁操作檢查、不需要存檔的小測試 |
| `presets/` | 範圍設定 |
