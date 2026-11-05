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
                                              │ Cloudflare Worker│ 檢視網頁、MCP
                                              └────────┬─────────┘
                                         手機、電腦 ◀──┴──▶ AI（MCP）
```

### 看地圖

用手機或電腦打開地圖網址就能看，不用登入。地圖是公開的（作者決定，2026-11-05），知道網址的人都看得到，見下面的「安全」。

介面是 Material 3 風格（作者從 iOS 風格和 Material 3 兩個預覽裡選的），深色、淺色跟著裝置的設定。

- 第一次打開看到四座主要的島；放大可以看到每一格方塊。世界範圍外填海水的顏色，手機上不會有黑邊（舊備份的海水顏色不同，切換過去時看得到世界主體的方形邊界）
- 點上方的搜尋列打開備份清單，清單依日期分組。切換備份時地圖位置不變，可以對照前後的差別
- 左下角顯示座標：用滑鼠時是游標的位置，用手機時是畫面中央十字的位置
- 右下角的「存成圖片」把目前畫面的地圖存成 PNG（不含按鈕和中央的十字），檔名帶著備份編號和座標。想要更多細節就先放大再存。移動地圖時這顆按鈕會收成圖示
- 沒有「全圖」按鈕（作者決定），縮小就看得到全貌。拖曳範圍限制在世界主體再往外 30%，不會滑進一片海裡回不來；所以遠處的零星區域（X 約 9 萬，以及座標 10 萬、100 萬、3000 萬附近）網頁上到不了，要看的話用下面的 AI 查地圖
- 放大、縮小的按鈕只有電腦才顯示，手機用雙指
- 網址會記住目前的備份、位置和縮放，直接複製網址就能分享或存成書籤；存成書籤要看最新備份的話，存不帶 `#` 的網址

### 安裝成 app

地圖可以從瀏覽器裝成 app，有自己的圖標，打開時沒有網址列。

- Android 的 Chrome：右上角選單 →「加到主畫面」或「安裝應用程式」
- iPhone 的 Safari：分享 →「加入主畫面」

做法和要注意的地方：

- 圖標在 `viewer/icons/`，是世界真實的島嶼輪廓。`maskable-512.png` 給 Android 裁成各種形狀，島留在中央的安全範圍內；`apple-touch-icon.png` 給 iPhone，不可以透明
- 沒有用 Service Worker：地圖只在連線時看，也避免舊網頁留在快取裡

### 地圖的外觀

作者決定的外觀（2026-11-05），畫進圖磚裡，所以網頁上沒有開關，手機和 AI 看到的都一樣：

| 項目 | 做法 | 在哪裡 |
| --- | --- | --- |
| 3d 影子 | `--shadows=3d` | 程式固定加 |
| 水不隨生態域變色 | 關掉水的色調和所有生態域的特殊顏色（海洋色塊、沼澤的水等等） | `unmined/map-settings.json` |
| 草不隨生態域變色 | 關掉草的色調，再把草方塊和矮草指定成同一個顏色 `#7c9656` | `unmined/map-settings.json`、`unmined/custom.blockstyles.txt` |
| 樹葉 | 維持生態域的色調（作者沒有要求統一） | |

地圖功能只做影子和輸出圖片，不做圖層（作者決定）。

改這兩個檔案之後，幾乎所有圖磚的內容都會變，下一次更新會重傳整份（這次 4215 張、52 MB）。舊的備份維持當時的樣子，切換時看得到差別。

實測學到的：

- 單純關掉草的色調，整片草會變成很亮的黃綠色（樣式表的 `map.land`），所以要另外指定顏色。`#7c9656` 是北邊大島平原原本的顏色
- 原本偏橘褐色的山坡也是生態域的草色，統一之後跟著變綠
- `custom.biometints.txt` 改不動基岩版原版的生態域：uNmINeD 先讀它，接著讀原版色調表，原版的值會蓋過去（紀錄看得到兩份都讀了，圖一個像素都沒變）。要用 `custom.blockstyles.txt`
- uNmINeD 只讀自己 `config` 資料夾裡的 `custom.blockstyles.txt`，沒有參數可以指定別的位置，所以 `backup.js` 每次渲染前會複製過去。更新 uNmINeD 把它蓋掉也沒關係，下次渲染會補回來
- `--mapsettings` 要吃電腦版存出來的完整格式，少了外層的欄位（連空物件 `{}` 也一樣）會當掉（`NullReferenceException`）。`map-settings.json` 就是作者用電腦版 0.19.54 存的檔案改的，0.20.11-dev 讀得懂
- 帶著設定檔時，檔案裡的 `Shadows` 和 `--shadows=false` 都關不掉影子，實際看的是 `ShadowMode`（0 = `2d`、1 = `3d`）或 `--shadows=2d` 這類參數

### AI 查地圖（MCP）

Worker 的 `/mcp` 是一個 MCP 伺服器，AI 可以用這些工具：

| 工具 | 用途 |
| --- | --- |
| `list_snapshots` | 列出所有備份（時間、備註） |
| `get_map_info` | 世界主體的座標範圍、遠處的零星區域、縮放等級 |
| `view_map` | 看某個座標周圍的俯視圖（回傳圖片，附上每張圖的座標範圍），例如「看 (1200, -340) 附近蓋了什麼」 |
| `find_changes` | 比較兩次備份，找出有變動的區域，例如「上次備份之後蓋了哪些地方」 |

雙擊 `setup-mcp.bat` 會把它加到 Claude Code（見下方「換電腦時重新設定」），**新開的對話才會生效**。不需要權杖。一次只接受一個呼叫，不支援批次（原因見「費用」）。claude.ai 網頁版和 App 的「連接器」應該也能直接加，這是推測，還沒試過。

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

已經在作者的電腦上設定好了。Cloudflare 那邊的東西（R2、Worker）都不用重做，換電腦時只要做第 1、3、5 步；R2 權杖的密鑰看不到是正常的，第 3 步建一組新的，舊的順手撤銷。

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

完成後會顯示網址（`https://asuka-map.<子網域>.workers.dev`），填進設定檔的 `map.url`。

改了 `worker/` 或 `viewer/` 底下的程式才要重新部署；平常備份只傳圖磚，不用部署。

#### 5. 給 AI 用的 MCP

雙擊 `setup-mcp.bat`，它會用 `claude mcp add` 把地圖的 MCP 加到 `%USERPROFILE%\.claude.json`。地圖是公開的，不需要權杖。

#### 想改回只有自己看

地圖原本用 Cloudflare Access 限制登入，2026-11-05 作者決定公開後拿掉了。想改回來的話：

1. Workers & Pages → `asuka-map` → **Access** 分頁 → **Protect this Worker behind Access**，範圍選 **All traffic**，政策選 **Cloudflare account**。**不要選 Email domain 再填 `gmail.com`，那樣所有 Gmail 使用者都能登入**
2. 想再加一層檢查的話，從 git 紀錄找回 `worker/src/access.js`（Worker 自己再驗一次 Access 的簽章，就算 Access 被關掉也不會公開），`ACCESS_TEAM_DOMAIN`、`ACCESS_AUD` 兩個機密還留在 Worker 上

已經公開過的內容收不回來，別人可能存過圖。

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

渲染時程式固定加上這些參數：

- `--force`（每次全部重畫）：uNmINeD 判斷「有沒有變動」時看不到 LevelDB 的 `.log`，而基岩版關遊戲時最新的改動就只在 `.log`，不強制的話地圖會默默停在舊的樣子（實測，見下方）。內容相同的圖磚畫出來也完全相同，所以不會多傳
- `--imageformat=webp`：預設的 JPEG 在 0.20.11-dev 一存檔就當掉（`InvalidOperation_NoValue`）。要換格式時在 `unmined.extraArgs` 指定，但要先清空 `map.renderDir`，因為同一份地圖不能混用兩種格式
- `--mapsettings`、`--shadows=3d`：見「地圖的外觀」

### 費用

全部在 Cloudflare 的免費額度內（2026-11-05 查的公告數字）。R2 啟用時可能要綁信用卡；超過額度才收費，Cloudflare 沒有「超過就自動停」的上限。

| 項目 | 免費額度 | 目前用量 |
| --- | --- | --- |
| R2 儲存空間 | 每月 10 GB | 107 MB（目前 5 次備份，其中兩份是改外觀前後各一整份圖磚） |
| R2 寫入 | 每月 100 萬次 | 整份重傳一次約 4200 次，只有改外觀時才會 |
| R2 讀取 | 每月 1000 萬次 | 看地圖時每張新圖磚一次，看過的留在瀏覽器快取 |
| Workers 請求 | 每天 10 萬次 | 地圖資料和 MCP 才算，網頁本身的檔案不算；幾個人看不會碰到 |
| Workers 運算 | 每次請求 10 毫秒 CPU | 實測五個 MCP 工具都沒有超過 |

每次備份增加多少要看改了多少（只傳有變動的圖磚，每次另外加一份 142 KB 的清單）。實測放一小塊方塊增加不到 1 MB；假設每次改 50 個區域，約增加 4 MB，10 GB 可以撐約 2000 次，這是推測。

地圖公開之後，費用的上限這樣算（Workers 免費方案）：

- 超過每天 10 萬次請求時，Cloudflare 回傳 Error 1027，世界協調時間午夜重置，地圖當天打不開但不收費
- R2 讀取全部要經過 Worker。一個請求最多讀 6 個物件（MCP 的 `view_map`：備份清單、這次備份的清單、4 張圖磚），所以就算有人每天灌滿，一個月最多約 1800 萬次，超過免費額度的部分約 3 美元（依公告的每百萬次 0.36 美元推算）
- 為了這個上限，MCP 不接受一次送多個呼叫

### 安全

- 地圖是公開的（作者決定，2026-11-05）：檢視網頁、地圖資料、MCP 都不用登入。看得到的內容是地圖圖磚、每次備份的日期和備註、存檔名，沒有玩家資料
- 網站只能讀：Worker 沒有會改資料的功能，地圖資料的網址只接受 GET 和 HEAD，路徑也限定格式
- 世界備份不公開：在 Google Drive，而且有 restic 的密碼
- R2 的 bucket 不公開（`r2.dev` 網址是關閉的），只能透過 Worker 讀取；上傳要用 `rclone.conf` 裡的 R2 金鑰
- `robots.txt` 請搜尋引擎不要收錄，主要是減少機器人流量，不算保護
- 機密都在 repo 外面：`%USERPROFILE%\.config\asuka\` 底下的 `rclone.conf`（R2 金鑰）、`restic-password.txt`（備份密碼）

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
| 之後每次渲染 | 全部重畫，無影子時實測 56 秒到 2 分 41 秒，作者第二次雙擊（連同備份、上傳）約 4 分鐘。開 3d 影子後約 4 分 20 秒（只測過一次，同時還有另一個小渲染在跑） |
| 套用新外觀 | 全部圖磚內容都變，重傳 4215 張、52 MB，上傳約 2 分 20 秒。真的世界前後修改時間沒變 |
| 世界沒動時重跑 | 開 3d 影子後作者雙擊：畫 4540 張、新上傳 0 張，重畫的結果完全相同，不會白傳 |
| 存成圖片 | 用真實圖磚在本機測過：四種縮放（含超過原始解析度）、像素比 1、2、2.625、3、電腦和手機尺寸，存出的圖和畫面一致、圖磚之間沒有縫。作者在手機上確認可以 |
| 介面 | 正式首頁用真實圖磚在本機測過（手機尺寸、深色和淺色）：切換備份、拖曳關閉面板、存成圖片（圖裡沒有黑色區域）。拖到邊界會停住，從很遠的座標打開也會拉回來，縮小看得到島。作者在手機上看過，沒有要改的 |
| 安裝成 app | 作者在 Android 手機上裝好，確認可以正常使用 |
| 只傳有變動的 | 全部重畫 4540 張，沒變的畫出來位元組完全相同。放一塊方塊只上傳 7 張（一張地面圖加上往外 6 個縮放等級各一張），雲端增加不到 1 MB |
| 作者雙擊 | 作者親手雙擊 `backup.bat` 三次都成功（快照 `ca6c106a`、`d7ca027a`、`46cc2721`） |
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
- [x] 手機登入後看地圖是否順暢：作者確認可以
- [x] Claude Code 透過 MCP 呼叫 `view_map` 能不能看懂圖：看得懂

還沒測過：

- iPhone 上的介面和安裝
- iPhone 上按「存成圖片」
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
├── worker/                Cloudflare Worker：地圖資料、MCP
│   ├── wrangler.jsonc
│   └── src/
└── test/                  自動測試
```

需要 Node.js 22 以上，不需要安裝任何套件：

```
cd tools/world-backup
npm test
```
