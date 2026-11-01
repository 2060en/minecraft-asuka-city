# 廣告清單（畫的替換表）

把原版的「畫」換成廣告時用的填空表。每一列是一個可以替換的畫，「廣告內容」欄留給作者填。做法與限制見[附加內容開發](addon.md#可以換成廣告的畫)。

> 編號對照圖：`addon/drafts/ads/slots.png`，框的大小照實際比例（1 格 = 1 方塊）。尺寸寫成「寬 × 高」，設定尺寸照 1 格約 0.75 公尺換算。

---

## 用法（已定）

- **常用的廣告用畫**：同一個廣告會在很多地方重複出現時，用畫
- **特定地點的廣告用 Image map 的地圖畫**：地圖畫比較耗效能，不能到處放；而且每一格會各自受光線影響，相鄰的格子明暗會斷層。所以只用在少數特定的看板、招牌
- **同一種尺寸裡，放畫時是隨機挑一幅**：同一種尺寸的廣告最好可以互相替換，或接受要重放幾次
- **拔掉附加內容後**：顯示原版的畫

---

## 2 × 1（1.5 × 0.75 公尺）

適合：車廂裡的橫式廣告、店頭的橫幅

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| A1 | Pool | `kz.png` (0, 32) | | |
| A2 | Courbet | `kz.png` (32, 32) | | |
| A3 | Sea | `kz.png` (64, 32) | | |
| A4 | Sunset | `kz.png` (96, 32) | | |
| A5 | Creebet | `kz.png` (128, 32) | | |

## 1 × 2（0.75 × 1.5 公尺）

適合：車站、機場的直式海報，柱子廣告

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| B1 | Wanderer | `kz.png` (0, 64) | | |
| B2 | Graham | `kz.png` (16, 64) | | |
| B3 | prairie_ride | `prairie_ride.png` | | |

## 2 × 2（1.5 × 1.5 公尺）

適合：牆面海報

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| C1 | Match | `kz.png` (0, 128) | | |
| C2 | Bust | `kz.png` (32, 128) | | |
| C3 | Stage | `kz.png` (64, 128) | | |
| C4 | Void | `kz.png` (96, 128) | | |
| C5 | SkullAndRoses | `kz.png` (128, 128) | | |
| C6 | Wither | `kz.png` (160, 128) | | |
| C7 | baroque | `baroque.png` | | |
| C8 | humble | `humble.png` | | |

## 3 × 3（2.25 × 2.25 公尺）

適合：大型牆面海報

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| D1 | bouquet | `bouquet.png` | | |
| D2 | cavebird | `cavebird.png` | | |
| D3 | cotan | `cotan.png` | | |
| D4 | endboss | `endboss.png` | | |
| D5 | fern | `fern.png` | | |
| D6 | owlemons | `owlemons.png` | | |
| D7 | sunflowers | `sunflowers.png` | | |
| D8 | tides | `tides.png` | | |

## 4 × 2（3 × 1.5 公尺）

適合：橫式看板

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| E1 | Fighters | `kz.png` (0, 96) | | |
| E2 | changing | `changing.png` | | |
| E3 | finding | `finding.png` | | |
| E4 | lowmist | `lowmist.png` | | |
| E5 | passage | `passage.png` | | |

## 3 × 4（2.25 × 3 公尺）

適合：直式大型看板

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| F1 | backyard | `backyard.png` | | |
| F2 | pond | `pond.png` | | |

## 4 × 3（3 × 2.25 公尺）

適合：橫式大型看板

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| G1 | Skeleton | `kz.png` (192, 64) | | |
| G2 | DonkeyKong | `kz.png` (192, 112) | | |

## 4 × 4（3 × 3 公尺）

適合：大樓牆面、屋頂看板

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| H1 | Pointer | `kz.png` (0, 192) | | |
| H2 | Pigscene | `kz.png` (64, 192) | | |
| H3 | BurningSkull | `kz.png` (128, 192) | | |
| H4 | orb | `orb.png` | | |
| H5 | unpacked | `unpacked.png` | | |

## 2 × 2，只能靠改存檔放

放畫時遊戲不會挑到這四幅，要用外部工具改存檔裡那幅畫的圖案名稱才會出現。適合放在固定位置、只出現一次的廣告。要不要用，待決定。

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| X1 | Earth | `kz.png` (0, 160) | | |
| X2 | Wind | `kz.png` (32, 160) | | |
| X3 | Fire | `kz.png` (64, 160) | | |
| X4 | Water | `kz.png` (96, 160) | | |

## 1 × 1（0.75 × 0.75 公尺）

| 編號 | 原版的畫 | 檔案 | 廣告內容 | 備註 |
| --- | --- | --- | --- | --- |
| S1 | Kebab | `kz.png` (0, 0) | 筆電：桌面 | 已定，見 `addon/drafts/laptop/` |
| S2 | Aztec | `kz.png` (16, 0) | 筆電：寫程式 | 已定 |
| S3 | Alban | `kz.png` (32, 0) | | |
| S4 | Aztec2 | `kz.png` (48, 0) | | |
| S5 | Bomb | `kz.png` (64, 0) | | |
| S6 | Plant | `kz.png` (80, 0) | | |
| S7 | Wasteland | `kz.png` (96, 0) | | |
| S8 | meditative | `meditative.png` | | |

`kz.png` 在 `textures/painting/`，括號是圖案在圖裡的左上角座標（像素）；其他檔案也在同一個資料夾。所有畫的背面與側邊共用 `kz.png` 右上角 (192, 0) 那一塊，已經換成筆電的灰色上蓋。
