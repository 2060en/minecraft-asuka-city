# 世界備份與雲端地圖

雙擊 `backup.bat`，一次做完：

1. 確認 Minecraft 已經關閉
2. 用 restic 把世界備份到 Google Drive（只存有變動的部分）
3. 用 uNmINeD 渲染網頁地圖（只重畫有變動的區域）
4. 把有變動的圖磚上傳到 Cloudflare R2
5. 在 [`docs/backup-log.md`](../../docs/backup-log.md) 加一行備份紀錄

之後在任何地方用手機或電腦打開網址，就能看到每一次備份時的地圖，也可以切換日期。AI（例如 Claude Code）可以透過 MCP 查地圖。

> **狀態：開發中，還沒實際跑過。** 各部分都有自動測試：上傳流程、登入驗證、MCP 工具、檢視網頁（用瀏覽器實際打開，手機和電腦的大小都測過），整個備份流程也用假的 restic、uNmINeD、rclone 跑過。但還沒有接上真正的 Google Drive、Cloudflare 和你的世界，見下方「待驗證」。

```
筆電（Minecraft 關閉時）                         雲端
┌───────────────────────┐   restic + rclone   ┌──────────────────┐
│ 世界資料夾            │ ──────────────────▶ │ Google Drive     │ 備份
│        │ uNmINeD      │                     └──────────────────┘
│        ▼              │   rclone            ┌──────────────────┐
│ 網頁地圖（圖磚）      │ ──────────────────▶ │ Cloudflare R2    │ 地圖資料
└───────────────────────┘   只傳有變動的      │        │         │
                                              │ Cloudflare Worker│ 檢查登入、檢視網頁、MCP
                                              └────────┬─────────┘
                                         手機、電腦 ◀──┴──▶ AI（MCP）
```

## 一次性設定

### 1. 安裝工具

在 PowerShell 執行：

```
winget install OpenJS.NodeJS.LTS
winget install restic.restic
winget install Rclone.Rclone
```

uNmINeD 的命令列版（CLI）要另外下載：到 [unmined.net/downloads](https://unmined.net/downloads/) 下載 Windows 64-bit 的 CLI，解壓縮到例如 `C:\tools\unmined-cli\`。

### 2. Google Drive（備份）

```
rclone config
```

新增一個叫 `gdrive` 的遠端，類型選 `drive`（Google Drive），照指示在瀏覽器登入。

接著建立 restic 的密碼檔（例如 `%USERPROFILE%\.config\asuka\restic-password.txt`，裡面放一行夠長的密碼，**要另外記在密碼管理器**，弄丟就無法還原備份），然後初始化備份庫：

```
restic -r rclone:gdrive:minecraft-backup --password-file %USERPROFILE%\.config\asuka\restic-password.txt init
```

### 3. Cloudflare（雲端地圖）

需要一個 Cloudflare 帳號，免費方案就夠了。

1. **建立 R2 儲存空間**：Cloudflare 主控台 → R2 → 建立 bucket，名稱 `asuka-map`
2. **R2 的 API 權杖**：R2 → 管理 API 權杖 → 建立，權限選「物件讀寫」、只限 `asuka-map`。記下 Access Key ID、Secret Access Key 和帳號 ID，然後：

   ```
   rclone config create r2 s3 provider=Cloudflare access_key_id=<Access Key ID> secret_access_key=<Secret Access Key> endpoint=https://<帳號 ID>.r2.cloudflarestorage.com acl=private no_check_bucket=true
   ```

3. **部署 Worker**：

   ```
   cd tools\world-backup\worker
   npx wrangler login
   npx wrangler deploy
   ```

   完成後會顯示網址，例如 `https://asuka-map.<你的子網域>.workers.dev`。這時候打開會看到「尚未設定 Cloudflare Access」，這是正常的：沒設定登入之前，地圖不會開放給任何人。

4. **設定登入（Cloudflare Access）**：Cloudflare 主控台 → Zero Trust → Access → Applications → 新增 Self-hosted 應用程式
   - 網域填 Worker 的網址（`asuka-map.<你的子網域>.workers.dev`）
   - 新增一條政策：動作「Allow」，條件「Emails」填你自己的 email
   - 儲存後複製應用程式的「Application Audience (AUD) Tag」
   - 在 Zero Trust → Settings 找到團隊網域（`<團隊名稱>.cloudflareaccess.com`）
   - 把兩者填進 `worker/wrangler.jsonc` 的 `ACCESS_AUD` 和 `ACCESS_TEAM_DOMAIN`，再執行一次 `npx wrangler deploy`

   Cloudflare 的介面常改版，選單名稱可能不完全一樣；Worker 的設定頁裡也可能有直接幫 workers.dev 網址開啟 Access 的選項。

5. **給 AI 用的服務權杖**（要用 MCP 才需要）：Zero Trust → Access → Service Auth → 建立 Service Token，記下 Client ID 和 Client Secret。回到第 4 步的應用程式，再新增一條政策：動作「Service Auth」，條件「Service Token」選剛建立的權杖。

### 4. 設定檔

把 `config.example.json` 複製成 `config.json`（不會被 commit），填入：

| 欄位 | 說明 |
| --- | --- |
| `worldPath` | 世界資料夾。可以用 `%APPDATA%` 這類環境變數，路徑用 `/` 分隔 |
| `minecraftProcesses` | Minecraft 的程式名稱，用來確認已經關閉。如果備份時沒有擋下開著的 Minecraft，在工作管理員確認名稱後改這裡 |
| `restic.repository` | restic 備份庫，預設 `rclone:gdrive:minecraft-backup` |
| `restic.passwordFile` | restic 密碼檔 |
| `restic.forget` | 清理舊快照的規則，例如 `["--keep-daily", "7", "--keep-monthly", "24"]`。空的就全部保留（保留規則還沒決定） |
| `unmined.exe` | `unmined-cli.exe` 的位置 |
| `unmined.extraArgs` | 額外的渲染選項。執行 `unmined-cli web help render` 可以看有哪些 |
| `rclone.remote` | 上傳目的地，預設 `r2:asuka-map` |
| `map.renderDir` | uNmINeD 渲染結果的資料夾，**不要刪**，下次才能只重畫有變動的區域 |
| `map.stateDir` | 記錄哪些圖磚已經上傳過，**不要刪** |

## 使用

雙擊 `backup.bat`，輸入這次的備註（例如「蓋好 AKQ 第二航廈」，可以留空），等它跑完。第一次渲染整張地圖會比較久，之後只重畫有變動的區域。

跑完之後記得把 `docs/backup-log.md` commit。

| 參數 | 用途 |
| --- | --- |
| `--note "文字"` | 直接給備註，不用輸入 |
| `--skip-backup` | 不做 restic 備份，只更新地圖 |
| `--skip-map` | 只做 restic 備份，不更新地圖 |
| `--publish-only` | 不備份、不渲染，只重新上傳（上次上傳失敗時用） |

例如在 PowerShell：`node backup.js --skip-backup --note "只更新地圖"`

### 看地圖

用手機或電腦打開 Worker 的網址，第一次會要求輸入 email，收驗證碼登入。手機可以「加入主畫面」，用起來像 App。

- 上方的選單切換備份日期，地圖位置不變，可以對照前後的差別
- 右上角顯示座標：用滑鼠時是游標的位置，用手機時是畫面中央十字的位置
- 網址會記住目前的備份、位置和縮放，直接複製網址就能分享或存成書籤

## AI 查地圖（MCP）

Worker 的 `/mcp` 是一個 MCP 伺服器，AI 可以用這些工具：

| 工具 | 用途 |
| --- | --- |
| `list_snapshots` | 列出所有備份（時間、備註） |
| `get_map_info` | 地圖涵蓋的座標範圍、縮放等級 |
| `view_map` | 看某個座標周圍的俯視圖（回傳圖片，附上每張圖的座標範圍），例如「看 (1200, -340) 附近蓋了什麼」 |
| `find_changes` | 比較兩次備份，找出有變動的區域，例如「上次備份之後蓋了哪些地方」 |

加到 Claude Code（把 `<…>` 換成第 3 步記下的值）：

```
claude mcp add --transport http asuka-map https://asuka-map.<你的子網域>.workers.dev/mcp --header "CF-Access-Client-Id: <Client ID>" --header "CF-Access-Client-Secret: <Client Secret>"
```

目前只支援可以自訂標頭的 MCP 用戶端（例如 Claude Code）。claude.ai 網頁版和 App 的「連接器」要用 OAuth 登入，還沒做。

### 第二階段：方塊資料（待決定）

目前的工具看的是渲染好的俯視圖，看得到顏色和形狀，但不知道「座標 (x, y, z) 是什麼方塊」，也看不到屋頂底下。要做到這一點，要在備份時另外把方塊資料從存檔讀出來、上傳到雲端，再加上 `get_block`、`get_column`、`describe_area` 這類工具。做法與取捨記在 [`docs/technical.md`](../../docs/technical.md) 的「雲端地圖」。

## 費用

都在 Cloudflare 的免費額度內：

- R2：每月 10 GB 儲存、100 萬次寫入、1000 萬次讀取免費，讀取流量不收費
- Workers：每天 10 萬次請求免費（看地圖時每張圖磚算一次）
- Zero Trust（Access）：50 人以內免費

## 安全

- 所有網址（檢視網頁、地圖資料、MCP）都要先通過 Cloudflare Access 登入
- Worker 會再驗一次 Access 的簽章：就算 Access 被關掉或設定錯誤，地圖也不會變成公開的，只會顯示錯誤訊息
- R2 的 bucket 不公開，只能透過 Worker 讀取
- restic 的備份有加密，Google Drive 上看不到內容；密碼弄丟就無法還原

## 雲端的資料格式

| 路徑 | 內容 |
| --- | --- |
| `index.json` | 所有備份的清單，新的在前面 |
| `snapshots/<備份編號>.json` | 這次備份的地圖：每個縮放等級、每張圖磚對應到哪個雜湊值，以及 uNmINeD 的地圖設定 |
| `tiles/<前兩碼>/<雜湊值>.png` | 圖磚本身。內容一樣的圖磚只存一份，大部分地形不會變，所以每次備份增加的量很小 |

備份編號是備份開始的時間，例如 `2026-11-01-2130`。

## 待驗證

- [ ] uNmINeD CLI 能渲染現在的基岩版世界，渲染整張地圖要多久、多大
- [ ] restic 透過 rclone 備份到 Google Drive 是否順利、要多久
- [ ] rclone 上傳到 R2 是否順利
- [ ] Cloudflare Access 的設定步驟（介面可能和上面寫的不同）
- [ ] 手機登入後看地圖是否順暢
- [ ] Claude Code 透過 MCP 呼叫 `view_map` 能不能看懂圖
- [ ] GDK 版 Minecraft 的程式名稱（用來確認已經關閉）

## 開發

```
tools/world-backup/
├── backup.js              入口：備份、渲染、上傳、紀錄
├── backup.bat             Windows 雙擊執行
├── config.example.json    設定範例
├── lib/
│   ├── tiles.js           uNmINeD 圖磚路徑、地圖設定、清單格式（純計算）
│   ├── publish.js         掃描圖磚、只準備有變動的部分、上傳
│   ├── run.js             執行外部程式、確認 Minecraft 是否開著
│   └── report.js          備份紀錄
├── viewer/                檢視網頁（Leaflet 1.9.4，BSD 2-Clause 授權）
├── worker/                Cloudflare Worker：登入驗證、地圖資料、MCP
│   ├── wrangler.jsonc
│   └── src/
└── test/                  自動測試
```

需要 Node.js 22 以上，不需要安裝任何套件：

```
cd tools/world-backup
npm test
```
