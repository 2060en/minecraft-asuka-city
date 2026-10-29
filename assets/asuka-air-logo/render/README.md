# 塗裝渲染

用 three.js 程序化建模的 Boeing 787-8，加上 Asuka Air 塗裝，渲染成 `../livery-*.png`。

```bash
npm install three@0.170.0 playwright
python3 -m http.server 8765 --bind 127.0.0.1
node shot.js out.png "view=side&w=4800&h=2000"
```

- `view`：`side`（側面）、`hero`（左前方）、`tail`（尾翼特寫）、`rear`（右後方）
- 輸出的圖再縮小一半做超取樣
- 塗裝畫在 `main.js` 的 `paintSide()`：以側視圖座標（公尺）繪製，再依機體表面位置投影上去
- `mark.js` 是標誌的幾何，來自 `../mark.svg`
