# CLAUDE.md

這個 repo 用來管理作者在 Minecraft 基岩版建造了約 10 年的架空島國世界，國名為茉波（Mahaki，2026-11-09 由津蘭賀千良改名），首都為 Asuka City（飛鳥市）。repo 主要是設定文件；`addon/` 放自製附加內容 Asuka tech（`addon/pack/` 是資源包與行為包，`addon/drafts/` 是外觀草稿）與材質包 Rail to Belt（`addon/rail_to_belt/`）。附加內容的作者一律寫「asuka tech」，介紹（description）一律用英文，`tools/preview/` 是外觀預覽工具，`tools/converter/` 是轉換程式（只讀的掃描 `scan.py`、轉出原味版的 `convert.py`），`tools/asuka-toolkit/` 是 Asuka toolkit（獨立的行為包，不併進 Asuka tech），`tools/world-backup/` 是世界備份工具（雙擊備份到 Google Drive 與還原，同時更新 Cloudflare 上的雲端地圖；改程式後跑 `npm test`，改了 `worker/` 或 `viewer/` 要重新部署），`tools/world-model/` 是區域 3D 模型（只讀世界的副本，把一個範圍做成 3D 網頁與平面圖；範圍設定在 `presets/`），`tools/commerce-list/` 是商業清單（把 `docs/world/commerce.md` 的品牌一覽做成 HTML）。

## 文件地圖

| 文件 | 內容 |
| --- | --- |
| `docs/technical.md` | 遊戲版本、工具、結構方塊、存檔備份、建造技術歷史、技術面的待辦 |
| `docs/backup-log.md` | 備份紀錄：`tools/world-backup/backup.js` 每次備份自動加一行。作者雙擊後這個檔案會有未提交的修改，看到時順手一起提交 |
| `docs/addon.md` | 自製附加內容（資源包＋行為包）：雙版本與轉換程式、對照表、基岩版的技術限制、構想清單 |
| `docs/addon-contents.md` | 附加內容清單：Asuka tech 做了哪些東西（改材質、改圖示、新增方塊、新增實體），每加一樣東西都要更新 |
| `docs/ads.md` | 廣告清單：可以換成廣告的畫，一幅一列的填空表 |
| `docs/scale.md` | 遊戲尺寸與設定尺寸的換算、人口與量體基準 |
| `docs/world/overview.md` | 設計原則、國家定位、氣候、歷史人文、法律、國防、人物與組織、待決定事項 |
| `docs/world/geography.md` | 各地區的設施與參考地 |
| `docs/world/transport.md` | 鐵路、地鐵、公路、海運、航空與交通的待決定事項 |
| `docs/world/flight-schedule.md` | AKQ 機場的一週航班與 Asuka Air 機隊（主要版本在作者的 Google 試算表） |
| `docs/world/asuka-air-logo.md` | Asuka Air 標誌：符號與字體分開處理；主要用無邊框、透明背景的標，圓形標備用（檔案在 `assets/asuka-air/`） |
| `docs/world/telecom.md` | 第一大電信公司 Spoton（子品牌 Homie）：以 Spark 為藍本（紫色、星形），logo、沿革、業務、色彩、量體（logo 原圖在 `assets/spoton/`） |
| `docs/world/post.md` | 郵政 Maha Post（茉波郵便）：以 NZ Post 為藍本，只做郵件與物流；名稱、logo（正方形的信封，旗幟紅）、業務、沿革、據點、郵筒、AKQ 機場的櫃台（logo 檔在 `assets/maha-post/`） |
| `docs/world/banks.md` | 四大銀行：公股的茉波銀行，加上國泰世華、三井住友、KB國民三家外國銀行的子行；每家一種木頭色調（AKQ 提款機） |
| `docs/world/akq-food-court.md` | AKQ 3F 美食街：自創店家的品牌故事、各店菜單（日本現價、含稅）、告示牌的寬度推算與照打文字 |
| `docs/world/commerce.md` | 商業：商家、品牌、店鋪、餐廳與商業活動的共用原則、商業版圖、品牌與店家一覽。作者想到什麼講什麼，Claude 邊討論邊整理進來；每次回覆都用 `python3 tools/commerce-list/build.py --save` 產生 HTML 清單，用 SendUserFile 附上 |
| `docs/world/akq-departure-hall.md` | AKQ 出境大廳東側：由北到南各櫃台、電梯、廁所、全家、出發口、郵局的告示牌文字與共用原則（垂直牌、電梯樓層顯示、便利商店以廣告為主） |
| `docs/world/naming.md` | 命名原則、討論流程、黑名單、命名素材、地名分層、地區風格、地名表、候補名單 |
| `docs/world/asuka-inc.md` | Asuka Inc.：本國唯一的本土財團，控股與各全資子公司（地產、航空、旅遊、重工、科技電子、電信、百貨）、投資的公司 |
| `docs/world/bunker.md` | Asuka Inc. 總部地堡：總指揮、世界控制室、生活設施、監獄、戰備地鐵 |
| `docs/build-checklist.md` | 設施清單與完成狀態、城市細節、參考建築、商店品牌 |
| `docs/prologue.md` | 新玩家序章：出生點、開場橋段、入境流程 |

討論新主題前，先讀相關文件，避免和既有設定矛盾。

## 對話與記錄方式

- 一律使用繁體中文（台灣用語）
- 對話中出現的新設定或決定，整理進對應的文件，然後 commit 並 push；沒有適合的文件時再新增，並更新 `README.md` 的文件列表
- 只把作者確認過的內容寫成設定；Claude 提出的建議，在作者同意前放在「待決定事項」
- 狀態標記：已定、暫定、待決定、待補
- 附加內容每新增、修改或拿掉一樣東西，都要同時更新 `docs/addon-contents.md`（作者要求，2026-11-04）
- 店家、品牌的詳細內容（品牌故事、完整菜單、價格）都要寫進文件保存；遊戲裡沒放的也不能刪（作者 2026-11-10）
- 寫告示牌文字前，先看 `docs/world/akq-food-court.md` 的[告示牌](docs/world/akq-food-court.md#告示牌)：一行的寬度，以及字體的規則（同一個地方的告示牌，英文要不要單獨一行要統一，作者 2026-11-10）
- 要用方塊字在告示牌上拼大英文字（一個字母 3 格寬、4 行高，跨好幾塊板子）、大漢字（含書法風）、紅色印章，或在告示牌上畫箭頭、逃生出口小人這類符號時，用技能 `.claude/skills/drawing-big-sign-letters/`，不要手排；只有文字時先問作者要靠左還是置中（作者 2026-11-11）
- 告示牌可以用 `§` 顏色代碼（例如 `§4` 深紅），不顯示也不佔寬度，同一塊牌子能混不同顏色（2026-11-12 春水堂印章確認）。新設計的方塊字畫只用左右兩邊都畫到的方塊字（█▀▄▁▂▃▅▆▇▔▙▛▜▟▚▞）；只畫一半或一小條的（▌▐▘▝▖▗▏▕ 等）在遊戲裡會變窄、排歪
- Claude 沒辦法刪除 GitHub 上的分支（作者測試過很多次），分支一律由作者自己刪，不要提議代刪。PR 合併後 GitHub 會自動刪掉分支（作者刻意開啟），之後的工作從最新的 main 重新開分支

## 設計原則

作者很重視合理性，但也允許為了個人滿足或地方特色而保留的「不合理」。討論設定時：

- 用現實先例檢驗合理性，指出明顯不合理的地方，並提出讓它站得住腳的方式
- 作者明確標記為「刻意的特色」的項目（例如黒潮特快的工程難度、沖繩群島成為本國領土的經過與人口），不再追究
- 量體要配合人口規模，對照 `docs/scale.md` 的量體基準；國家富裕可以解釋品質，不能解釋超出需求的量體
- 除了合理性，也要考慮豐富度：內容撐不起來、大部分時間空著的設施（例如只有幾班飛機的航廈），即使合理也會很無聊；要嘛併進其他建築或不蓋，要嘛合理地補足內容（例如增加航班與航點），補的內容一樣要用現實先例檢驗
- 命名時，對作者的現實意義（通常是作者喜歡的人事物）是重點，再替名字編設定上的由來；流程見 `docs/world/naming.md`。小店、小餐廳的店名不用命名素材，直接取一般的名字
- 提出任何名字前，先查 `docs/world/naming.md` 的黑名單，名單上的詞絕對不能用
- 名字的漢字一律用日文漢字（例如寿豊、与那国）；作者的輸入法打出來是繁體，記錄時要轉換。文件的敘述仍用繁體中文

## 外觀設計

自製附加內容的外觀在對話中討論，流程見 `docs/addon.md` 的「外觀設計流程」。草稿放在 `addon/drafts/<名稱>/`，預覽圖這樣產生：

```bash
cd tools/preview && npm install && cd ../..
python3 addon/drafts/<名稱>/build.py
node tools/preview/render.mjs addon/drafts/<名稱>/preview.json addon/drafts/<名稱>/preview.png
```

算出來的預覽圖先自己看過，再傳給作者。

## 建造原則

盡量原汁原味：不使用會影響世界內容的模組或行為包，外加內容必須「拔掉之後不影響體驗」。遊戲內建的指令、作弊模式、結構方塊都可以使用。詳見 `docs/technical.md`。

例外是作者自製的附加內容，採用雙版本：主世界可以使用自製方塊，但隨時都要能用轉換程式轉出原味版。每一個自製的東西都要有好的原版替代，想不到就先不做。提案新的自製內容時，一併提出原版替代。詳見 `docs/addon.md`。
