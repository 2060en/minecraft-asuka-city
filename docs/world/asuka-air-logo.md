# Asuka Air 標誌

Asuka Air（IS）的標誌。檔案在 [`assets/asuka-air/`](../../assets/asuka-air/)，對照圖是 [`preview.png`](../../assets/asuka-air/preview.png)。

---

## 組成

標誌分成兩個部分，**分開處理**：

| 部分 | 內容 | 狀態 |
| --- | --- | --- |
| 符號 | 三條 S 形的風線加一個圓點，白色；放在黑色正方形或黑色圓形裡；線條兩端流線收尖 | 已定 |
| 字體 | 「ASUKA AIR」，黑色無襯線大寫，放在符號右側 | 已定，之後再處理 |

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

## 待決定事項

- [x] 符號端點：採用流線收尖
- [ ] 縮到 32 px 時尖端會變細，是否要另做小尺寸用的版本
- [ ] 字體：作者覺得目前的字體太呆板，之後另外處理
