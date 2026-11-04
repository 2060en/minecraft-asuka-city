# 世界備份與雲端地圖

雙擊 `backup.bat`，把主世界 `CX198` 備份到 Google Drive。備份有加密，每次只傳有變動的部分。

> **狀態**
> - **備份、還原：已實測**，見下方「實測紀錄」。
> - **雲端地圖：還沒接**。程式寫好了，但只用假工具和自動測試跑過，預設關閉，見下方「雲端地圖」。

## 平常使用

1. 關掉 Minecraft（開著的話程式會擋下來，不會備份）
2. 雙擊 `backup.bat`
3. 輸入這次的備註（例如「蓋好 AKQ 第二航廈」，可以留空直接按 Enter）
4. 看到「完成」後按任意鍵關掉視窗

每次備份會在 [`docs/backup-log.md`](../../docs/backup-log.md) 加一行紀錄。這個檔案要提交（把修改存進 git 紀錄）才會留在 repo，下次請 Claude 一起提交就好；就算沒提交也不影響備份本身。

備份時只讀取世界資料夾，不會寫入。目前全部的備份都會保留（保留規則還沒決定，見 [`docs/technical.md`](../../docs/technical.md) 第 6 節）。

## 還原

雙擊 `restore.bat`，選要還原哪一份（直接按 Enter 是最新的）。

- 只會還原到新的資料夾 `%USERPROFILE%\AsukaRestore\<時間>`，**不會碰世界資料夾**
- 還原完會和目前的世界逐檔比對。世界在那次備份之後玩過的話，有差異是正常的
- 要拿回遊戲裡用：先關掉 Minecraft，把還原出來的資料夾整個複製到 `minecraftWorlds` 底下，換個資料夾名稱，遊戲裡會多出一個世界
- 不需要的話，還原出來的資料夾可以直接刪掉

想確認備份還健康時，也可以偶爾跑一次當作演練。

## 電腦壞掉時

要拿回世界，只需要兩樣東西：

1. **restic 密碼**（作者另外存的那一份。沒有密碼就永遠打不開，沒有其他辦法）
2. **Google 帳號**（備份在 Google Drive 的 `minecraft-backup` 資料夾）

在新電腦上：

1. 照下面的「一次性設定」做第 1、2、4、5 步，**不要做第 6 步**（第 6 步會建新的備份庫）
2. 第 4 步需要的憑證，到 [Google Cloud 的用戶端頁面](https://console.cloud.google.com/auth/clients)，在專案 `asuka-backup` 的 `rclone` 用戶端新增一組密鑰（舊的密鑰看不到是正常的）
3. 雙擊 `restore.bat`

**要用同一個用戶端**：rclone 的權限只能碰自己建立的檔案，換一個新用戶端很可能看不到舊備份（官方文件沒明寫，這是依權限規則的推測）。如果用戶端被刪掉了（網路上有人引述 Google 的警告說閒置 6 個月可能被刪，沒查到官方原文），檔案還在 Google Drive 上，可以從網頁把 `minecraft-backup` 整個資料夾下載下來，用 restic 直接還原（這條路的實測範圍見下方「實測紀錄」）：

```
restic -r <下載下來的資料夾> --password-file <密碼檔> restore latest --target <還原到哪裡>
```

## 一次性設定

已經在作者的電腦上設定好了，換電腦時才要重做。

### 1. 安裝工具

在 PowerShell 執行：

```
winget install --id OpenJS.NodeJS.LTS -e
winget install --id restic.restic -e
winget install --id Rclone.Rclone -e
```

winget 裝的 restic 檔名帶版本號（例如 `restic_0.19.1_windows_amd64.exe`），也不一定建得出 `restic` 這個別名，程式會自己到 winget 的安裝資料夾找。

### 2. 密碼檔

建立 `%USERPROFILE%\.config\asuka\restic-password.txt`，整個檔案只放一行密碼（建議 20 個字以上），**另外存一份**到密碼管理器或抄在紙上。這個檔案不可以進 repo。

### 3. 建立自己的 Google 憑證

rclone 內建的共用憑證 [2026 年內會停用](https://rclone.org/drive/#making-your-own-client-id)，所以要用自己的。作者的憑證已經建好（專案 `asuka-backup`），換電腦時不用重建，直接跳到第 4 步。

要重建的話，在 [Google Cloud](https://console.cloud.google.com/) 用有備份的那個帳號：

1. [建立專案](https://console.cloud.google.com/projectcreate)
2. [啟用 Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
3. 到[驗證平台](https://console.cloud.google.com/auth/overview)按「開始使用」，填名稱和電子郵件，目標對象選「外部」
4. 在[資料存取](https://console.cloud.google.com/auth/scopes)新增範圍 `https://www.googleapis.com/auth/drive.file`
5. 在[品牌](https://console.cloud.google.com/auth/branding)填首頁和隱私權政策連結（都填 `https://2060en.github.io/asuka-backup-app/`，這個小頁面放在 [asuka-backup-app](https://github.com/2060en/asuka-backup-app)），授權網域填 `2060en.github.io`。沒填的話下一步的按鈕是灰的
6. 在[目標對象](https://console.cloud.google.com/auth/audience)按「發布應用程式」。不發布的話，登入每 7 天會過期
7. 在[用戶端](https://console.cloud.google.com/auth/clients)建立用戶端，類型選「電腦版應用程式」。「讓 AI 代理使用這個用戶端」不用勾

### 4. 連上 Google Drive

雙擊 `setup-gdrive.bat`，貼上 Client ID 和 Client secret，在跳出來的瀏覽器登入並同意。憑證和權杖存在 `%USERPROFILE%\.config\asuka\rclone.conf`，不在 repo 裡；rclone 會把權杖印出來，所以這個工具不顯示那段輸出。

不用 rclone 預設的 `%APPDATA%\rclone\rclone.conf`：從 Claude 桌面版啟動的程式寫進 `%APPDATA%` 時，Windows 會導到 Claude 專屬的資料夾，作者雙擊時就找不到。所以要自己執行 rclone 時，記得加上 `--config %USERPROFILE%\.config\asuka\rclone.conf`。

權限是 `drive.file`：rclone 只能碰自己建立的檔案，看不到 Google Drive 裡的其他東西。

### 5. 設定檔

把 `config.example.json` 複製成 `%USERPROFILE%\.config\asuka\world-backup.json`，把 `<使用者編號>` 換成 `%APPDATA%\Minecraft Bedrock\Users` 底下的資料夾名稱。設定檔放在 repo 外面，換分支、換工作資料夾都不用重設。

| 欄位 | 說明 |
| --- | --- |
| `worldPath` | 世界資料夾。可以用 `%APPDATA%` 這類環境變數，路徑用 `/` 分隔 |
| `minecraftProcesses` | Minecraft 的程式名稱，用來確認已經關閉 |
| `restic.exe`、`rclone.exe` | 程式名稱或完整路徑。只給名稱時會先找 PATH，再找 winget 的安裝資料夾 |
| `restic.repository` | restic 備份庫，預設 `rclone:gdrive:minecraft-backup` |
| `restic.passwordFile` | restic 密碼檔 |
| `restic.forget` | 清理舊快照的規則，例如 `["--keep-daily", "7", "--keep-monthly", "24"]`。空的就全部保留 |
| `map.enabled` | 要不要更新雲端地圖，預設 `false`。其他 `map.*`、`unmined.*`、`rclone.remote` 都是地圖用的 |

### 6. 建立備份庫

**只有第一次才做。已經有備份時不要做。**

```
restic -r rclone:gdrive:minecraft-backup --password-file %USERPROFILE%\.config\asuka\restic-password.txt init
```

## 實測紀錄

2026-11-05 在作者的電腦上跑過（Windows 11、restic 0.19.1、rclone 1.75.2、Node.js 24）：

| 項目 | 結果 |
| --- | --- |
| 第一次備份 | 主世界 620 個檔案、1.149 GiB，花 4 分 41 秒。Google Drive 上 76 個檔案、1.145 GiB |
| 還原 | `restore.js` 從 Google Drive 還原花 3 分 12 秒，620 個檔案逐一比對內容，**全部一模一樣** |
| 不會改動世界 | 第一次備份前和第二次備份後，620 個檔案的大小與修改時間都沒有變 |
| 遊戲開著時 | Minecraft 開在主畫面時，程式有偵測到並擋下來，沒有碰世界資料夾 |
| 作者雙擊 | 作者雙擊 `backup.bat`、輸入中文備註，備份完成（快照 `3fe79bee`），世界沒變動所以只多 3.9 KB |
| 最壞情況的退路 | 把 `minecraft-backup` 整個資料夾下載到本機，不靠 rclone，直接用 restic 列出備份、完整檢查所有資料，沒有發現錯誤 |

還沒測過：

- 把還原出來的世界放回 `minecraftWorlds`、在遊戲裡打開（內容逐檔相同，所以應該沒問題，這是推測）
- `restore.bat` 由作者親手雙擊（還原是 Claude 用同一支程式執行的）
- 從 Google Drive **網頁**下載資料夾（上面的退路是用 rclone 下載的。網頁下載時 Google 可能分成好幾個壓縮檔，要解壓縮到同一個資料夾，這是推測）
- 發布後的登入能撐多久（作者的憑證是 2026-11-05 發布的）

## 雲端地圖（第二段，還沒接）

> **狀態：程式寫好了，還沒實際跑過。** 上傳流程、登入驗證、MCP 工具、檢視網頁都有自動測試（或用瀏覽器打開測過），但還沒接上真正的 uNmINeD、Cloudflare 和世界。要啟用時照「啟用步驟」做，把設定檔的 `map.enabled` 改成 `true`。

啟用之後，雙擊 `backup.bat` 會多做兩件事：用 uNmINeD 渲染網頁地圖（只重畫有變動的區域），把有變動的圖磚上傳到 Cloudflare R2。之後在任何地方用手機或電腦打開網址，就能看到每一次備份時的地圖，也可以切換日期。AI（例如 Claude Code）可以透過 MCP 查地圖。

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

### 啟用步驟

#### 1. uNmINeD

命令列版（CLI）要另外下載：到 [unmined.net/downloads](https://unmined.net/downloads/) 下載 Windows 64-bit 的 CLI，解壓縮到例如 `C:\tools\unmined-cli\`，把路徑填進設定檔的 `unmined.exe`。

#### 2. Cloudflare

需要一個 Cloudflare 帳號，免費方案就夠了。

1. **建立 R2 儲存空間**：Cloudflare 主控台 → R2 → 建立 bucket，名稱 `asuka-map`
2. **R2 的 API 權杖**：R2 → 管理 API 權杖 → 建立，權限選「物件讀寫」、只限 `asuka-map`。記下 Access Key ID、Secret Access Key 和帳號 ID，然後：

   ```
   rclone --config %USERPROFILE%\.config\asuka\rclone.conf config create r2 s3 provider=Cloudflare access_key_id=<Access Key ID> secret_access_key=<Secret Access Key> endpoint=https://<帳號 ID>.r2.cloudflarestorage.com acl=private no_check_bucket=true
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

#### 3. 設定檔

把 `map.enabled` 改成 `true`。其他欄位：

| 欄位 | 說明 |
| --- | --- |
| `unmined.exe` | `unmined-cli.exe` 的位置 |
| `unmined.extraArgs` | 額外的渲染選項。執行 `unmined-cli web help render` 可以看有哪些 |
| `rclone.remote` | 上傳目的地，預設 `r2:asuka-map` |
| `map.renderDir` | uNmINeD 渲染結果的資料夾，**不要刪**，下次才能只重畫有變動的區域 |
| `map.stateDir` | 記錄哪些圖磚已經上傳過，**不要刪** |

地圖啟用後可以用這些參數：

| 參數 | 用途 |
| --- | --- |
| `--skip-backup` | 不做 restic 備份，只更新地圖 |
| `--skip-map` | 只做 restic 備份，不更新地圖 |
| `--publish-only` | 不備份、不渲染，只重新上傳（上次上傳失敗時用） |

`--note "文字"` 不管有沒有地圖都能用，可以直接給備註，不用輸入。例如在 PowerShell：`node backup.js --skip-backup --note "只更新地圖"`

### 看地圖

用手機或電腦打開 Worker 的網址，第一次會要求輸入 email，收驗證碼登入。手機可以「加入主畫面」，用起來像 App。

- 上方的選單切換備份日期，地圖位置不變，可以對照前後的差別
- 右上角顯示座標：用滑鼠時是游標的位置，用手機時是畫面中央十字的位置
- 網址會記住目前的備份、位置和縮放，直接複製網址就能分享或存成書籤

### AI 查地圖（MCP）

Worker 的 `/mcp` 是一個 MCP 伺服器，AI 可以用這些工具：

| 工具 | 用途 |
| --- | --- |
| `list_snapshots` | 列出所有備份（時間、備註） |
| `get_map_info` | 地圖涵蓋的座標範圍、縮放等級 |
| `view_map` | 看某個座標周圍的俯視圖（回傳圖片，附上每張圖的座標範圍），例如「看 (1200, -340) 附近蓋了什麼」 |
| `find_changes` | 比較兩次備份，找出有變動的區域，例如「上次備份之後蓋了哪些地方」 |

加到 Claude Code（把 `<…>` 換成第 2 步記下的值）：

```
claude mcp add --transport http asuka-map https://asuka-map.<你的子網域>.workers.dev/mcp --header "CF-Access-Client-Id: <Client ID>" --header "CF-Access-Client-Secret: <Client Secret>"
```

目前只支援可以自訂標頭的 MCP 用戶端（例如 Claude Code）。claude.ai 網頁版和 App 的「連接器」要用 OAuth 登入，還沒做。

目前的工具看的是渲染好的俯視圖，看得到顏色和形狀，但不知道「座標 (x, y, z) 是什麼方塊」，也看不到屋頂底下。要做到這一點，要在備份時另外把方塊資料從存檔讀出來、上傳到雲端，再加上 `get_block`、`get_column`、`describe_area` 這類工具（待決定）。

### 費用

依 Cloudflare 公布的免費額度（還沒實際用過）：

- R2：每月 10 GB 儲存、100 萬次寫入、1000 萬次讀取免費，讀取流量不收費
- Workers：每天 10 萬次請求免費（看地圖時每張圖磚算一次）
- Zero Trust（Access）：50 人以內免費

### 安全

- 所有網址（檢視網頁、地圖資料、MCP）都要先通過 Cloudflare Access 登入
- Worker 會再驗一次 Access 的簽章：就算 Access 被關掉或設定錯誤，地圖也不會變成公開的，只會顯示錯誤訊息
- R2 的 bucket 不公開，只能透過 Worker 讀取

### 雲端的資料格式

| 路徑 | 內容 |
| --- | --- |
| `index.json` | 所有備份的清單，新的在前面 |
| `snapshots/<備份編號>.json` | 這次備份的地圖：每個縮放等級、每張圖磚對應到哪個雜湊值，以及 uNmINeD 的地圖設定 |
| `tiles/<前兩碼>/<雜湊值>.png` | 圖磚本身。內容一樣的圖磚只存一份，大部分地形不會變，所以每次備份增加的量很小 |

備份編號是備份開始的時間，例如 `2026-11-01-2130`。

### 待驗證

- [ ] uNmINeD CLI 能渲染現在的基岩版世界，渲染整張地圖要多久、多大
- [ ] rclone 上傳到 R2 是否順利
- [ ] Cloudflare Access 的設定步驟（介面可能和上面寫的不同）
- [ ] 手機登入後看地圖是否順暢
- [ ] Claude Code 透過 MCP 呼叫 `view_map` 能不能看懂圖

## 開發

```
tools/world-backup/
├── backup.js              入口：備份、渲染、上傳、紀錄
├── backup.bat             Windows 雙擊執行
├── restore.js             入口：還原到新資料夾並比對
├── restore.bat            Windows 雙擊執行
├── setup-gdrive.js        一次性設定：讓 rclone 連上 Google Drive
├── setup-gdrive.bat       Windows 雙擊執行
├── config.example.json    設定範例
├── lib/
│   ├── config.js          讀設定檔、restic 的環境變數
│   ├── restore.js         世界在快照裡的路徑、比對資料夾
│   ├── tiles.js           uNmINeD 圖磚路徑、地圖設定、清單格式（純計算）
│   ├── publish.js         掃描圖磚、只準備有變動的部分、上傳
│   ├── run.js             執行外部程式、尋找程式位置、確認 Minecraft 是否開著
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
