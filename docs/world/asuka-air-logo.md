# Asuka Air 標誌

Asuka Air（IS）的標誌。檔案在 [`assets/asuka-air/`](../../assets/asuka-air/)，使用示範是 [`preview.png`](../../assets/asuka-air/preview.png)。

---

## 組成

標誌分成符號和字體兩個部分，**分開處理**。

| 部分 | 內容 | 狀態 |
| --- | --- | --- |
| 符號 | 三條 S 形的風線加一個圓點，線條兩端流線收尖 | 已定 |
| 字體 | 「ASUKA AIR」，Syne Bold，全大寫 | 已定 |
| 主要標誌 | 無邊框的符號放在字的左側，背景透明 | 已定 |
| 圓形標 | 黑色圓形裡放白色符號，再接字體 | 已定，只當備用 |

- 只有黑白兩色
- 原圖：[符號](../../assets/asuka-air/original/asuka-air-symbol-original.png)、[符號加字體](../../assets/asuka-air/original/asuka-air-logo-original.png)

---

## 使用規則

作者決定：**平常一律用無邊框的標誌**。圓形標很像以前的泛美航空，很老氣，盡量不用，但還是保留，以備需要時使用。

- 無邊框的符號和字體一樣，背景透明，不加底色
- 依背景的深淺選顏色：淺色底用黑色，深色底用白色
- 圓形標只用在淺色底

| 檔案 | 內容 | 用途 |
| --- | --- | --- |
| `asuka-air-logo.svg` / `-white.svg` | 符號加字體，黑色／白色，透明背景 | 主要標誌 |
| `asuka-air-wordmark.svg` / `-white.svg` | 只有字 | 空間窄、或符號已經出現在別處 |
| `asuka-air-symbol-lines.svg` / `-white.svg` | 只有符號 | 尾翼、App 圖示、小尺寸標記 |
| `asuka-air-logo-circle.svg` | 圓形標加字體 | 備用 |
| `asuka-air-symbol-circle.svg` | 只有圓形標 | 備用 |
| `asuka-air-symbol-square.svg` | 黑色正方形加白色符號，1024 px | 原本的方形圖示；也是其他檔案線條的來源 |

---

## 符號

作者決定：線條的起筆收筆**不要用圓頭**，改成流線的收尖（採用「流線」方案；另一個「葉形」方案沒有採用）。構圖、線條路徑、粗細、圓點都和原圖相同。

- 線條路徑從原圖描出來，只改兩端的寬度：線身維持原本的粗細（1024 px 版約 43 px），接近端點時逐漸變細成尖端
- 起筆（左端）：較長的細尾，約 170 px 逐漸收細
- 收筆（右端）：較短的尖頭，約 70 px
- 圓點不是線條，維持圓形
- 長度以 1024 px 的正方形版為準

---

## 字體

作者覺得原本的無襯線字體太呆板，從四個方案（Marcellus、Syne、Michroma、Italiana）中選了 **Syne Bold**：現代的寬體，K 和 R 的造型有個性。

- 字距：0.07 em
- 字已經轉成外框，不需要安裝字型
- Syne 是 Google Fonts 上的 SIL Open Font License 字型，可以用在標誌
- 試過把 A 的橫槓換成流線收尖，效果像眼睛或魚，太刻意，不採用

---

## 主要標誌的比例

- 符號高度（線條加圓點）是字高的 1.5 倍，垂直置中對齊字
- 符號和字的間距是字高的 0.55 倍
- 圓形標的比例照原圖：字高約為圓形直徑的 35%，間距約為直徑的 23%

---

## 重新產生檔案

```bash
python3 -I assets/asuka-air/tools/taper.py assets/asuka-air/original/asuka-air-symbol-original.png assets/asuka-air
```

```bash
python3 -I assets/asuka-air/tools/wordmark.py Syne-Bold.ttf assets/asuka-air
```

- `taper.py`：從原圖描出線條、加上收尖，輸出正方形和圓形的符號；需要 `numpy`、`Pillow`
- `wordmark.py`：把 Syne 轉成外框，輸出字、無邊框符號與各種組合；需要 `fonttools` 和 Syne Bold 字型檔
- 要調整收尖長度、字距或比例，改程式裡的數字再重新產生

---

## 待決定事項

- [ ] 縮到 32 px 時尖端會變細，是否要另做小尺寸用的版本
- [ ] 中日文名稱與字體（目前只有英文名 Asuka Air）
