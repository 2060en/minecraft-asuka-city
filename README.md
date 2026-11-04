# minecraft-asuka-city

這個 repo 用於製作與討論我的 Minecraft 架空世界「Asuka City」，包含以下主題：

- 世界觀與相關設定
- 建築設計
- 都市設計
- 模組（Mod）開發
- 插件（Plugin）開發

## 文件

- [技術文檔](docs/technical.md)：遊戲版本、工具、附加內容、世界設定、結構方塊與存檔備份
- [附加內容開發](docs/addon.md)：專為這個世界製作的資源包與行為包，雙版本與轉換程式的做法、構想清單
- [附加內容清單](docs/addon-contents.md)：Asuka tech 目前做了哪些東西，分成改材質、改圖示、新增方塊、新增實體四類
- [廣告清單](docs/ads.md)：把原版的畫換成廣告的填空表，每一個可替換的畫一列
- [比例尺與尺寸規範](docs/scale.md)：遊戲尺寸與設定尺寸的換算原則
- [世界觀總覽](docs/world/overview.md)：設計原則、國家定位、氣候、歷史人文、法律與人物
- [地理與主要設施](docs/world/geography.md)：列島概要、各地區設施與參考地
- [交通](docs/world/transport.md)：鐵路、地鐵、公路、海運與航空
- [AKQ 航班表](docs/world/flight-schedule.md)：Asuka City 機場的一週航班與 Asuka Air 機隊
- [Asuka Air 標誌](docs/world/asuka-air-logo.md)：符號、字體、使用規則與檔案（`assets/asuka-air/`）
- [電信](docs/world/telecom.md)：第一大電信公司 Spoton（以 Spark 為藍本）的 logo、沿革、業務與色彩（logo 原圖在 `assets/spoton/`）
- [命名](docs/world/naming.md)：命名原則、黑名單、地名分層、地名表與 Keep 筆記中的候補地名
- [總部地堡](docs/world/bunker.md)：Asuka Inc. 總部地底的總指揮中心兼末日地堡
- [建造清單](docs/build-checklist.md)：Keep 筆記中的設施清單、城市細節、參考建築與品牌
- [新玩家序章](docs/prologue.md)：新玩家的出生點與開場橋段

## 其他資料夾

- `addon/pack/`：自製附加內容 Asuka tech 的資源包與行為包原始檔，`build.py` 組成可以安裝的 `.mcaddon`；`addon/mapping.json` 是原味版的對照表
- `addon/rail_to_belt/`：只換材質的材質包「Rail to Belt」，把鐵軌換成履帶的樣子
- `addon/drafts/`：自製附加內容的外觀草稿（模型、材質、預覽圖）
- `tools/preview/`：把基岩版模型算成預覽圖的工具
- `tools/converter/`：轉換程式：只讀的掃描與轉出原味版
- `tools/asuka-toolkit/`：Asuka 工具包：獨立的行為包，木棍快速建造與破壞、烈焰棒物品收藏、旋風棒拿特殊物品
