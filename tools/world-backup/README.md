# 世界備份與雲端地圖

雙擊 `backup.bat`，把主世界 `CX198` 備份到 Google Drive，同時更新雲端地圖。備份有加密，每次只傳有變動的部分。

> **狀態**
> - **備份、還原：已實測**，見下方「實測紀錄」。
> - **雲端地圖：已接上**，見下方「雲端地圖」和「地圖的實測紀錄」。

## 平常使用

1. 關掉 Minecraft（開著的話程式會擋下來，不會備份）
2. 雙擊 `backup.bat`
3. 輸入這次的備註（例如「蓋好 AKQ 第二航廈」，可以留空直接按 Enter）
4. 看到「完成」後按任意鍵關掉視窗

每次備份會在 [`docs/backup-log.md`](../../docs/backup-log.md) 加一行紀錄。這個檔案要提交（把修改存進 git 紀錄）才會留在 repo，下次請 Claude 一起提交就好；就算沒提交也不影響備份本身。

備份和渲染地圖時都只讀取世界資料夾，不會寫入。目前全部的備份都會保留（保留規則還沒決定，見 [`docs/technical.md`](../../docs/technical.md) 第 6 節）。

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
| `map.enabled` | 要不要更新雲端地圖，範例檔預設 `false`。其他 `map.*`、`unmined.*`、`rclone.remote`、`rclone.r2Endpoint` 都是地圖用的，見「雲端地圖」 |

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

## 雲端地圖

雙擊 `backup.bat` 除了備份，還會用 uNmINeD 渲染整張網頁地圖，只把有變動的圖磚上傳到 Cloudflare R2。之後在任何地方用手機或電腦打開網址，就能看到每一次備份時的地圖，也可以切換日期。AI（例如 Claude Code）可以透過 MCP 查地圖。

地圖網址在設定檔的 `map.url`，備份完成時也會顯示。這個 repo 是公開的，所以網址不寫在這裡。

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

### 看地圖

用手機或電腦打開地圖網址，第一次要登入 Cloudflare 帳號，登入一次維持 7 天（Access 的設定可以改）。手機可以「加入主畫面」，用起來像 App。

- 第一次打開看到世界主體的全貌；放大可以看到每一格方塊
- 上方的選單切換備份日期，地圖位置不變，可以對照前後的差別
- 右上角顯示座標：用滑鼠時是游標的位置，用手機時是畫面中央十字的位置
- 「全圖」按鈕回到世界主體。世界裡有遠到座標 3000 萬的零星區域，拖曳範圍不設限，迷路時按這個
- 網址會記住目前的備份、位置和縮放，直接複製網址就能分享或存成書籤；存成書籤要看最新備份的話，存不帶 `#` 的網址

### AI 查地圖（MCP）

Worker 的 `/mcp` 是一個 MCP 伺服器，AI 可以用這些工具：

| 工具 | 用途 |
| --- | --- |
| `list_snapshots` | 列出所有備份（時間、備註） |
| `get_map_info` | 世界主體的座標範圍、遠處的零星區域、縮放等級 |
| `view_map` | 看某個座標周圍的俯視圖（回傳圖片，附上每張圖的座標範圍），例如「看 (1200, -340) 附近蓋了什麼」 |
| `find_changes` | 比較兩次備份，找出有變動的區域，例如「上次備份之後蓋了哪些地方」 |

雙擊 `setup-mcp.bat` 會把它加到 Claude Code（見下方「換電腦時重新設定」），**新開的對話才會生效**。目前只支援可以自訂標頭的 MCP 用戶端（例如 Claude Code）。claude.ai 網頁版和 App 的「連接器」要用 OAuth 登入，還沒做。

目前的工具看的是渲染好的俯視圖，看得到顏色和形狀，但不知道「座標 (x, y, z) 是什麼方塊」，也看不到屋頂底下。要做到這一點，要在備份時另外把方塊資料從存檔讀出來、上傳到雲端，再加上 `get_block`、`get_column`、`describe_area` 這類工具（待決定）。

### 參數

| 參數 | 用途 |
| --- | --- |
| `--skip-backup` | 不做 restic 備份，只更新地圖 |
| `--skip-map` | 只做 restic 備份，不更新地圖 |
| `--publish-only` | 不備份、不渲染，只重新上傳（上次上傳失敗時用） |

`--note "文字"` 不管有沒有地圖都能用，可以直接給備註，不用輸入。例如在 PowerShell：`node backup.js --skip-backup --note "只更新地圖"`

地圖那段失敗（例如沒網路）時，世界還是會備份好，畫面會寫「世界已經備份好了，只有雲端地圖這次沒更新」，下次備份會一起補上。

### 換電腦時重新設定

已經在作者的電腦上設定好了。Cloudflare 那邊的東西（R2、Worker、Access）都不用重做，換電腦時只要做第 1、3、6 步；權杖的密鑰看不到是正常的，第 3、6 步各建一組新的，舊的順手撤銷。

Cloudflare 的介面常改版，以下是 2026-11-05 實際操作時的畫面。

#### 1. uNmINeD

到 [unmined.net/downloads](https://unmined.net/downloads/) 下載 Windows 64-bit 的 CLI（命令列版），解壓縮到 `C:\tools\unmined-cli\`，不用安裝。實測版本 0.20.11-dev；官網下載頁只列開發版這個頻道。授權：個人使用免費，禁止商業用途，也不能散布軟體本身，所以不放進 repo。

#### 2. R2 空間（只做一次）

需要一個 Cloudflare 帳號。第一次要到主控台的 R2 頁面啟用，這一步由帳號主人自己操作。然後：

```
cd tools\world-backup\worker
npx wrangler login
npx wrangler r2 bucket create asuka-map-apac --location apac
```

`--location apac` 讓資料放在亞太區，台灣看比較快。**這個位置提示只在名稱第一次建立時有效**：同一個名稱刪掉重建，會留在原本的位置（實際遇到，所以名稱是 `asuka-map-apac` 而不是 `asuka-map`）。

#### 3. R2 權杖

在 R2 的 **API Tokens** 頁面按 **Create Account API Token**：

- 權限選 **Object Read & Write**
- 範圍選 **Apply to specific buckets only**，選 `asuka-map-apac`
- TTL 選 **Forever**

建立後會顯示 **Access Key ID** 和 **Secret Access Key**（只顯示這一次）。雙擊 `setup-r2.bat` 貼上，存在 `%USERPROFILE%\.config\asuka\rclone.conf`，不在 repo 裡；它會實際寫入再刪掉一個小檔案，確認權杖能用。端點從設定檔的 `rclone.r2Endpoint` 讀，沒有的話會問。

#### 4. 部署 Worker

```
cd tools\world-backup\worker
npx wrangler deploy
```

完成後會顯示網址（`https://asuka-map.<子網域>.workers.dev`），填進設定檔的 `map.url`。這時候打開會看到「尚未設定 Cloudflare Access」，這是正常的：沒設定登入之前，地圖不會開放給任何人。

改了 `worker/` 或 `viewer/` 底下的程式才要重新部署；平常備份只傳圖磚，不用部署。

#### 5. 設定登入（Cloudflare Access）

1. Workers & Pages → `asuka-map` → **Access** 分頁 → **Protect this Worker behind Access**。第一次用 Zero Trust 的帳號會先要求完成設定（依官方文件要填付款資料，免費方案不收費；作者的帳號之前就設定過，沒有實際走過這段）
2. 範圍選 **All traffic**（Previews only 只保護預覽網址，正式地圖會沒有保護）
3. 政策選 **Cloudflare account**。**不要選 Email domain 再填 `gmail.com`，那樣所有 Gmail 使用者都能登入**；清單裡的「任何Google帳號」也不要選
4. 按 **Apply Access**
5. 把 Access 的兩個值存成 Worker 的機密。沒有登入時打開地圖網址，會轉址到 `https://<團隊>.cloudflareaccess.com/cdn-cgi/access/login/...?kid=<AUD>`，兩個值都在這串網址裡（Access 分頁的 **Application values** 也有）：

   ```
   cd tools\world-backup\worker
   npx wrangler secret put ACCESS_TEAM_DOMAIN
   npx wrangler secret put ACCESS_AUD
   ```

   不寫在 `wrangler.jsonc`：這個 repo 是公開的，而且寫在那裡的值每次部署都會蓋掉 Worker 上的設定。

Worker 會用這兩個值再驗一次 Access 的簽章，所以就算 Access 被關掉，地圖也不會變成公開的。

#### 6. 給 AI 用的服務權杖

AI 沒辦法用瀏覽器登入，要用服務權杖：

1. Zero Trust → **Access controls** → **Service credentials** → **Service Tokens** → **Create Service Token**，名稱 `claude-code`，期限 **Non-expiring**，按 **Generate token**
2. 雙擊 `setup-mcp.bat`，貼上 **Client ID** 和 **Client Secret**（只顯示這一次）。存在 `%USERPROFILE%\.config\asuka\map-token.json`，並用 `claude mcp add` 加到 `%USERPROFILE%\.claude.json`，都不在 repo 裡
3. Zero Trust → **Access controls** → **Policies** 新增政策：動作 **Service Auth**，Include 選 **Service Token** = `claude-code`
4. 回到 Worker 的 Access 分頁 → **Manage access** → **Add policy** 選剛才的政策 → **Save changes**。要保留原本的 `Cloudflare account members`，不然手機就登入不了

換電腦時第 3、4 步不用重做，只要新權杖換掉政策裡的舊權杖。

#### 7. 設定檔

| 欄位 | 說明 |
| --- | --- |
| `map.enabled` | `true` 才會更新地圖 |
| `map.url` | 地圖網址，備份完成時顯示、`setup-mcp.bat` 也會用 |
| `map.renderDir` | uNmINeD 渲染結果的資料夾。每次都全部重畫，所以刪掉也沒關係（刪區塊之後要刪掉，不然舊圖磚會留著） |
| `map.stateDir` | 記錄哪些圖磚已經上傳過、所有備份的清單，**不要刪** |
| `unmined.exe` | `unmined-cli.exe` 的位置 |
| `unmined.extraArgs` | 額外的渲染選項，執行 `unmined-cli web help render` 可以看有哪些 |
| `rclone.remote` | 上傳目的地，`r2:asuka-map-apac` |
| `rclone.r2Endpoint` | R2 的端點，`setup-r2.bat` 用 |

渲染時程式固定加上兩個參數：

- `--force`（每次全部重畫）：uNmINeD 判斷「有沒有變動」時看不到 LevelDB 的 `.log`，而基岩版關遊戲時最新的改動就只在 `.log`，不強制的話地圖會默默停在舊的樣子（實測，見下方）。內容相同的圖磚畫出來也完全相同，所以不會多傳
- `--imageformat=webp`：預設的 JPEG 在 0.20.11-dev 一存檔就當掉（`InvalidOperation_NoValue`）。要換格式時在 `unmined.extraArgs` 指定，但要先清空 `map.renderDir`，因為同一份地圖不能混用兩種格式

### 費用

全部在 Cloudflare 的免費額度內（2026-11-05 查的公告數字）。R2 啟用時可能要綁信用卡；超過額度才收費，Cloudflare 沒有「超過就自動停」的上限。

| 項目 | 免費額度 | 目前用量 |
| --- | --- | --- |
| R2 儲存空間 | 每月 10 GB | 55 MB（目前 3 次備份） |
| R2 寫入 | 每月 100 萬次 | 第一次上傳約 4200 次 |
| R2 讀取 | 每月 1000 萬次 | 看地圖時每張新圖磚一次，看過的留在瀏覽器快取 |
| Workers 請求 | 每天 10 萬次 | 同上；一個人看不會碰到 |
| Workers 運算 | 每次請求 10 毫秒 CPU | 實測五個 MCP 工具都沒有超過 |
| Zero Trust（Access） | 50 人以內 | 1 人 |

每次備份增加多少要看改了多少（只傳有變動的圖磚，每次另外加一份 142 KB 的清單）。實測放一小塊方塊增加不到 1 MB；假設每次改 50 個區域，約增加 4 MB，10 GB 可以撐約 2000 次，這是推測。

### 安全

- 所有網址（檢視網頁、地圖資料、MCP）都要先通過 Cloudflare Access 登入，沒登入的請求會轉到登入頁
- Worker 會再驗一次 Access 的簽章：就算 Access 被關掉或設定錯誤，地圖也不會變成公開的，只會顯示錯誤訊息
- R2 的 bucket 不公開（`r2.dev` 網址是關閉的），只能透過 Worker 讀取
- 機密都在 repo 外面：`%USERPROFILE%\.config\asuka\` 底下的 `rclone.conf`（R2 金鑰）、`map-token.json`（服務權杖），和 `%USERPROFILE%\.claude.json`（MCP 設定裡的服務權杖）

### 雲端的資料格式

| 路徑 | 內容 |
| --- | --- |
| `index.json` | 所有備份的清單，新的在前面 |
| `snapshots/<備份編號>.json` | 這次備份的地圖：每個縮放等級、每張圖磚對應到哪個雜湊值，互相分開的區域（第一塊是世界主體），以及 uNmINeD 的地圖設定 |
| `tiles/<前兩碼>/<雜湊值>.webp` | 圖磚本身。內容一樣的圖磚只存一份，大部分地形不會變，所以每次備份增加的量很小 |

備份編號是備份開始的時間，例如 `2026-11-01-2130`。

### 地圖的實測紀錄

2026-11-05 在作者的電腦上跑過（uNmINeD 0.20.11-dev、rclone 1.75.2、wrangler 4.157.0）：

| 項目 | 結果 |
| --- | --- |
| 能不能處理現在的基岩版世界 | 可以，102 萬個區塊全部成功，沒有失敗 |
| 不會改動世界 | 世界複本渲染前後，620 個檔案內容都相同；真的世界前後大小和修改時間都沒變（第一次渲染、作者兩次雙擊都查過） |
| 第一次渲染與上傳 | 渲染 58 秒，4540 張圖磚；內容相同的只存一份後 4217 張、54 MB，上傳 2 分 8 秒 |
| 之後每次渲染 | 全部重畫，實測 56 秒到 2 分 41 秒。作者第二次雙擊（連同備份、上傳）約 4 分鐘 |
| 只傳有變動的 | 全部重畫 4540 張，沒變的畫出來位元組完全相同。放一塊方塊只上傳 7 張（一張地面圖加上往外 6 個縮放等級各一張），雲端增加不到 1 MB |
| 作者雙擊 | 作者親手雙擊 `backup.bat` 兩次都成功（快照 `ca6c106a`、`d7ca027a`） |
| 手機 | 作者用手機登入看得到地圖，可以放大、拖曳，切換備份時位置不動，只有放的方塊消失又出現 |
| 位置與方向 | 從新舊圖片算出方塊在 X 587～607、Z -167～-146，作者確認位置對，所以座標和方向都沒有顛倒 |
| 沒登入看不到 | 首頁、程式檔、地圖資料、MCP 都轉到登入頁；假的登入資訊、錯誤的權杖密鑰也一樣；R2 的公開網址是關閉的 |
| MCP | 新開的 Claude Code 對話透過 `asuka-map` 呼叫四個工具都正常，`view_map` 回傳圖片，看得出跑道、飛機、河道。`find_changes` 比較真正有變動的兩次備份時，是用權杖直接呼叫同一個網址確認的，沒有再經過 Claude Code |
| 運算限制 | 五次 MCP 呼叫都沒有超過免費方案每次 10 毫秒 CPU 的限制 |
| 地圖失敗時 | 暫時把工具路徑改錯：世界照樣備份、紀錄照寫，畫面寫「世界已經備份好了，只有雲端地圖這次沒更新」 |
| Google Drive 的增量 | 作者兩次改動都很小，備份卻分別增加 182 MB、261 MB：遊戲開關時 LevelDB 會重整檔案，restic 看到的是新內容。空間 5 TB，不急 |

俯視圖只畫最上面。作者第一次放的門和活板門在屋頂底下（Y 72～74，上面有 Y 77、78 的屋頂），地圖就沒有變動，這是正常的，不是漏掉。

實測找到的問題見 [`docs/technical.md`](../../docs/technical.md) 第 6 節「雲端地圖」。

### 待驗證

- [x] uNmINeD CLI 能渲染現在的基岩版世界，渲染整張地圖要多久、多大：可以，見上表
- [x] rclone 上傳到 R2 是否順利：順利，見上表
- [x] Cloudflare Access 的設定步驟：介面和原本寫的不同，上面「換電腦時重新設定」已經改成實際的畫面
- [x] 手機登入後看地圖是否順暢：作者確認可以
- [x] Claude Code 透過 MCP 呼叫 `view_map` 能不能看懂圖：看得懂

還沒測過：

- 第一次用 Zero Trust 的帳號要怎麼設定（作者的帳號之前就設定過）
- 登入 7 天到期後，手機重新登入的流程
- 手機「加入主畫面」
- 大改世界時，地圖和備份每次增加多少（目前只測過放一小塊方塊）
- 換一台電腦重新設定
- 刪掉區塊之後舊圖磚的處理（上面寫的「要刪掉渲染資料夾」是依程式行為的推測）

## 開發

```
tools/world-backup/
├── backup.js              入口：備份、渲染、上傳、紀錄
├── backup.bat             Windows 雙擊執行
├── restore.js             入口：還原到新資料夾並比對
├── restore.bat            Windows 雙擊執行
├── setup-gdrive.js        一次性設定：讓 rclone 連上 Google Drive
├── setup-gdrive.bat       Windows 雙擊執行
├── setup-r2.js            一次性設定：讓 rclone 連上 Cloudflare R2
├── setup-r2.bat           Windows 雙擊執行
├── setup-mcp.js           一次性設定：把地圖的 MCP 加到 Claude Code
├── setup-mcp.bat          Windows 雙擊執行
├── config.example.json    設定範例
├── lib/
│   ├── config.js          讀設定檔、restic 的環境變數
│   ├── restore.js         世界在快照裡的路徑、比對資料夾
│   ├── tiles.js           uNmINeD 圖磚路徑、地圖設定、地圖分區、清單格式（純計算）
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
