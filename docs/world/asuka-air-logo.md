# Asuka Air 標誌

Asuka Air（IS）的標誌。檔案在 [`assets/asuka-air/`](../../assets/asuka-air/)，對照圖是 [`preview.png`](../../assets/asuka-air/preview.png)。

---

## 組成

標誌分成兩個部分，**分開處理**：

| 部分 | 內容 | 狀態 |
| --- | --- | --- |
| 符號 | 三條 S 形的風線加一個圓點，白色；放在黑色正方形或黑色圓形裡；線條兩端流線收尖 | 已定 |
| 字體 | 「ASUKA AIR」，黑色大寫，放在符號右側；作者覺得原本的無襯線字體太呆板，正在換 | 待決定 |

- 原圖：[符號](../../assets/asuka-air/original/asuka-air-symbol-original.png)、[符號加字體](../../assets/asuka-air/original/asuka-air-logo-original.png)
- 圓形版和正方形版是同一組線條，只差外框；圓形的直徑約為正方形邊長的 96%
- 只有黑白兩色

---

## 符號的端點修改

作者決定：線條的起筆收筆**不要用圓頭**，改成流線的收尖（2026-11 定案，採用「流線」方案）。構圖、線條路徑、粗細、圓點都不變。

- 線條路徑是從原圖描出來的，只改兩端的寬度：線身維持原本的粗細，接近端點時逐漸變細成尖端
- 起筆（左端）：較長的細尾，約 170 px 逐漸收細
- 收筆（右端）：較短的尖頭，約 70 px
- 圓點不是線條，維持圓形
- 長度以 1024 px 的正方形版為準
- 另一個方案「葉形」（兩端都約 110 px 收尖）沒有採用

| 檔案 | 內容 |
| --- | --- |
| `asuka-air-symbol-square.svg` | 黑色正方形加白色線條，對應原本的方形圖示 |
| `asuka-air-symbol-circle.svg` | 黑色圓形加白色線條，對應原本和字體並排的圓形版 |
| `asuka-air-symbol-lines.svg` | 只有線條和圓點，黑色、透明背景，給淺色底或其他配色使用 |

要重新產生或調整收尖長度，用 `assets/asuka-air/tools/taper.py`：

```bash
python3 -I assets/asuka-air/tools/taper.py assets/asuka-air/original/asuka-air-symbol-original.png assets/asuka-air
```

---

## 字體的修改

作者決定：原本的字體太呆板，要換成有設計感的字體。符號不動，橫式排列的比例照原圖：字高約為圓形直徑的 35%，字和圓形的間距約為直徑的 23%。

提案（對照圖：[`wordmark-options/preview.png`](../../assets/asuka-air/wordmark-options/preview.png)）：

| 方案 | 字型 | 特色 | 狀態 |
| --- | --- | --- | --- |
| 1 | Marcellus | 古典、優雅；收筆外擴成尖角，沒有圓頭，和流線符號同調。Claude 推薦 | 待決定 |
| 2 | Syne Bold | 現代寬體、粗；K 和 R 的造型有個性 | 待決定 |
| 3 | Michroma | 極寬的未來感，像高速列車或航太 | 待決定 |
| 4 | Italiana | 極細的高對比，精品感；和黑色圓形放一起偏輕 | 待決定 |

- 試過把 A 的橫槓換成和風線一樣的流線收尖，效果像眼睛或魚，太刻意，不採用
- 每個方案有兩個檔案：`optN-*.svg`（符號加字體）與 `optN-*-wordmark.svg`（只有字）
- 字已經轉成外框，不需要安裝字型；字型都是 Google Fonts 上的 SIL Open Font License，可以用在標誌
- 產生檔案用 `assets/asuka-air/tools/wordmark.py`（需要 `fonttools` 和字型檔）

---

## 待決定事項

- [x] 符號端點：採用流線收尖
- [ ] 縮到 32 px 時尖端會變細，是否要另做小尺寸用的版本
- [ ] 字體：從四個方案中選一個，或指定想要的感覺再調整
