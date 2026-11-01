# NPC 清單（皮膚的替換表）

把原版 NPC 的皮膚換成世界裡的人物時用的填空表。每一列是一個可以替換的皮膚，「人物」欄留給作者填。做法見[附加內容開發](addon.md)的 NPC 皮膚。

> 原版皮膚的對照圖用 `python3 addon/drafts/npc/vanilla_sheet.py` 產生（存到 `.scratch/npc_vanilla.png`，是 Mojang 的圖，不放進 repo）。編號照 NPC 設定畫面裡皮膚的順序（待實測）。Claude 提出的人物與做法，在作者同意前都放在最後的[待決定事項](#待決定事項)。

---

## 用法

- 原版 NPC 用 `/summon npc` 或 NPC 生成蛋放置，在 NPC 的設定畫面選皮膚、設定名字與對話；NPC 不會走動
- 資源包只換皮膚的圖，NPC 本身是原版的，所以拔掉附加內容後，NPC 還在，只是顯示原版的皮膚
- **按職業對應替換**（Claude 提案，待決定）：把世界裡的人物放在原版同一類的格子，例如站務員放在上班族、工人放在建築工人，原味版也還是同一種職業；N46～N50、N56～N60 是生物造型與機台，拿來當一般人的話，原味版會變成非人類
- 皮膚是 64 × 64，但排列**不是**玩家皮膚的格式，見下一節

---

## NPC 的模型（已查證，2026-11-01）

查 Mojang 官方的原版資源包（`models/entity/npc.geo.json`、`animations/npc.animation.json`、`render_controllers/npc.render_controllers.json`）整理。NPC 用的是**和村民同一型的模型**，不是玩家的身形。之前記錄的「玩家皮膚格式」是錯的。

| 部位 | 尺寸（像素） | 說明 |
| --- | --- | --- |
| 頭 | 8 × 10 × 8 | 比玩家的頭高 2 像素 |
| 鼻子 | 2 × 4 × 2 | 村民那種鼻子，從臉的下半部突出，比下巴多垂 1 像素。皮膚上畫成透明就看不到 |
| 身體 | 8 × 12 × 6 | 比玩家厚 2 像素 |
| 外袍 | 8 × 18 × 6，比身體大一圈 | 從肩膀蓋到離地 6 像素。可以畫成外套、大衣、背心、裙子；透明的地方露出裡面的身體與腳 |
| 手 | 永遠交叉在胸前 | 原版動畫固定的姿勢，沒有垂下來的手。兩隻手肘在兩端，手掌在中間交疊，可以讓 NPC「拿」東西（原版的老師拿著一本書） |
| 腳 | 4 × 12 × 4 | 兩隻腳共用同一張圖 |

- 帽子層的位置和頭對不齊（從下巴往上只蓋 8 像素），原版的人物都沒畫，自製皮膚也不畫；帽子、安全帽直接畫在頭上
- 模型本身也可以用資源包換掉（例如改成玩家的身形、手垂下來），但 60 個皮膚的排列都會跟著變，沒有重畫的原版皮膚會亂掉，遊戲更新時也比較容易壞。Claude 建議沿用原版的模型（待決定）

---

## 一般人物（npc_1 ～ npc_10）

原版的樣子：穿便服的一般人。N01～N05 是長髮、穿洋裝或裙子的女性，N06～N10 是穿便服的男性。適合：一般市民、乘客、遊客、路人。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N01 | 1 | `textures/entity/npc/npc_1.png` | | |
| N02 | 2 | `textures/entity/npc/npc_2.png` | | |
| N03 | 3 | `textures/entity/npc/npc_3.png` | | |
| N04 | 4 | `textures/entity/npc/npc_4.png` | | |
| N05 | 5 | `textures/entity/npc/npc_5.png` | | |
| N06 | 6 | `textures/entity/npc/npc_6.png` | | |
| N07 | 7 | `textures/entity/npc/npc_7.png` | | |
| N08 | 8 | `textures/entity/npc/npc_8.png` | | |
| N09 | 9 | `textures/entity/npc/npc_9.png` | | |
| N10 | 10 | `textures/entity/npc/npc_10.png` | | |

## 科學家（npc_scientist_1 ～ 10）

原版的樣子：N11～N18 穿白色實驗衣；N19 是黃色防護衣加防毒面具，N20 是灰色的方頭機器人。適合：醫師、護理師、研究員、藥局；N19 適合防護衣，N20 適合機器人。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N11 | scientist_1 | `textures/entity/npc/npc_scientist_1.png` | | |
| N12 | scientist_2 | `textures/entity/npc/npc_scientist_2.png` | | |
| N13 | scientist_3 | `textures/entity/npc/npc_scientist_3.png` | | |
| N14 | scientist_4 | `textures/entity/npc/npc_scientist_4.png` | | |
| N15 | scientist_5 | `textures/entity/npc/npc_scientist_5.png` | | |
| N16 | scientist_6 | `textures/entity/npc/npc_scientist_6.png` | | |
| N17 | scientist_7 | `textures/entity/npc/npc_scientist_7.png` | | |
| N18 | scientist_8 | `textures/entity/npc/npc_scientist_8.png` | | |
| N19 | scientist_9 | `textures/entity/npc/npc_scientist_9.png` | | 原版是黃色防護衣 |
| N20 | scientist_10 | `textures/entity/npc/npc_scientist_10.png` | | 原版是機器人 |

## 養蜂人（npc_apiary_1 ～ 5）

原版的樣子：N21 是穿養蜂防護衣、戴面紗的人，N22、N23 是穿工作服的人，N24 穿蜜蜂花紋的圍裙，N25 是蜜蜂頭的吉祥物。適合：防護裝備的工作人員、吉祥物。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N21 | apiary_1 | `textures/entity/npc/npc_apiary_1.png` | | 原版戴面紗 |
| N22 | apiary_2 | `textures/entity/npc/npc_apiary_2.png` | | |
| N23 | apiary_3 | `textures/entity/npc/npc_apiary_3.png` | | |
| N24 | apiary_4 | `textures/entity/npc/npc_apiary_4.png` | | |
| N25 | apiary_5 | `textures/entity/npc/npc_apiary_5.png` | | 原版是蜜蜂頭的吉祥物 |

## 老師（npc_teacher_1 ～ 5）

原版的樣子：穿便服的大人，N27 手上拿著一本書。適合：老師、學生、教授。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N26 | teacher_1 | `textures/entity/npc/npc_teacher_1.png` | | |
| N27 | teacher_2 | `textures/entity/npc/npc_teacher_2.png` | | |
| N28 | teacher_3 | `textures/entity/npc/npc_teacher_3.png` | | |
| N29 | teacher_4 | `textures/entity/npc/npc_teacher_4.png` | | |
| N30 | teacher_5 | `textures/entity/npc/npc_teacher_5.png` | | |

## 建築工人（npc_construction_1 ～ 5）

原版的樣子：戴安全帽、穿反光背心。適合：工地工人、機場地勤、鐵路維修、清潔人員。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N31 | construction_1 | `textures/entity/npc/npc_construction_1.png` | | |
| N32 | construction_2 | `textures/entity/npc/npc_construction_2.png` | | |
| N33 | construction_3 | `textures/entity/npc/npc_construction_3.png` | | |
| N34 | construction_4 | `textures/entity/npc/npc_construction_4.png` | | |
| N35 | construction_5 | `textures/entity/npc/npc_construction_5.png` | | |

## 農業（npc_Agriculture_1 ～ 10）

原版的樣子：農夫、園丁，工作服居多；N39 是稻草人。適合：農民、市場攤販、園丁、漁民。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N36 | Agriculture_1 | `textures/entity/npc/npc_Agriculture_1.png` | | |
| N37 | Agriculture_2 | `textures/entity/npc/npc_Agriculture_2.png` | | |
| N38 | Agriculture_3 | `textures/entity/npc/npc_Agriculture_3.png` | | |
| N39 | Agriculture_4 | `textures/entity/npc/npc_Agriculture_4.png` | | 原版是稻草人 |
| N40 | Agriculture_5 | `textures/entity/npc/npc_Agriculture_5.png` | | |
| N41 | Agriculture_6 | `textures/entity/npc/npc_Agriculture_6.png` | | |
| N42 | Agriculture_7 | `textures/entity/npc/npc_Agriculture_7.png` | | |
| N43 | Agriculture_8 | `textures/entity/npc/npc_Agriculture_8.png` | | |
| N44 | Agriculture_9 | `textures/entity/npc/npc_Agriculture_9.png` | | |
| N45 | Agriculture_10 | `textures/entity/npc/npc_Agriculture_10.png` | | |

## 生物造型的商人（npc_BusinessMobs_1 ～ 5）

原版的樣子：穿西裝、襯衫的動物頭角色（例如貓、熊貓、狐狸），不是人類。適合：吉祥物、玩偶裝；拿來當一般人的話，原味版會變成動物頭。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N46 | BusinessMobs_1 | `textures/entity/npc/npc_BusinessMobs_1.png` | | |
| N47 | BusinessMobs_2 | `textures/entity/npc/npc_BusinessMobs_2.png` | | |
| N48 | BusinessMobs_3 | `textures/entity/npc/npc_BusinessMobs_3.png` | | |
| N49 | BusinessMobs_4 | `textures/entity/npc/npc_BusinessMobs_4.png` | | |
| N50 | BusinessMobs_5 | `textures/entity/npc/npc_BusinessMobs_5.png` | | |

## 上班族（npc_EverydayBusiness_1 ～ 5）

原版的樣子：穿襯衫、西裝的上班族；N52 不是人，是辦公室的飲水機。適合：站務員、空服員、櫃台人員、店員、公務員；N52 適合機器。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N51 | EverydayBusiness_1 | `textures/entity/npc/npc_EverydayBusiness_1.png` | | |
| N52 | EverydayBusiness_2 | `textures/entity/npc/npc_EverydayBusiness_2.png` | | 原版是飲水機 |
| N53 | EverydayBusiness_3 | `textures/entity/npc/npc_EverydayBusiness_3.png` | | |
| N54 | EverydayBusiness_4 | `textures/entity/npc/npc_EverydayBusiness_4.png` | | |
| N55 | EverydayBusiness_5 | `textures/entity/npc/npc_EverydayBusiness_5.png` | | |

## 服務台（npc_Kiosk_1 ～ 5）

原版的樣子：不是人形，是帶螢幕的服務機台；N58 是飄在空中的小螢幕。適合：自助機台、導覽機、機器人。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N56 | Kiosk_1 | `textures/entity/npc/npc_Kiosk_1.png` | | |
| N57 | Kiosk_2 | `textures/entity/npc/npc_Kiosk_2.png` | | |
| N58 | Kiosk_3 | `textures/entity/npc/npc_Kiosk_3.png` | | 原版是小螢幕 |
| N59 | Kiosk_4 | `textures/entity/npc/npc_Kiosk_4.png` | | |
| N60 | Kiosk_5 | `textures/entity/npc/npc_Kiosk_5.png` | | |

---

## 草稿

草稿在 `addon/drafts/npc/`：`build.py` 用程式畫皮膚（存到 `skins/<名稱>.png`），`preview.png` 是正面與背面，`scene.png` 是放進車站、機場、晶圓廠的樣子。

### 第一輪：風格樣本（2026-11-01）

人物與格子都還沒決定，先畫幾個世界裡一定會出現的人，給作者看風格。照原版 16x 的像素風，布料加一點點淡淡的紋理。

| 草稿 | 檔案 | 內容 | 狀態 |
| --- | --- | --- | --- |
| 站務員 | `skins/station_staff.png` | 深藍制服與帽子、白襯衫、領帶、白手套，右手臂有紅色臂章 | 草稿 |
| 機師（Asuka Air） | `skins/pilot.png` | 黑色雙排扣制服、袖口金線、白頂的機師帽、胸前金色飛行章 | 草稿 |
| 空服員（Asuka Air） | `skins/flight_attendant.png` | 藍綠色外套與及膝裙、珊瑚色絲巾、盤髮 | 草稿，顏色暫定 |
| 晶圓廠無塵衣 | `skins/cleanroom.png` | 全白連身無塵衣與頭套、口罩、護目鏡、藍色手套、鞋套 | 草稿 |
| 工地工人 | `skins/construction_worker.png` | 白色安全帽、灰色工作服、螢光綠反光背心、棉手套 | 草稿 |
| 醫師 | `skins/doctor.png` | 及膝白袍、淺藍色手術服、聽診器、眼鏡、灰髮 | 草稿 |
| 觀光客 | `skins/tourist.png` | 遮陽帽、短袖 T 恤、後背包、牛仔褲、手上拿著相機 | 草稿 |

---

## 待決定事項

1. **要做哪些人物、放在哪些格子**：「人物」欄由作者填。Claude 依世界裡已有的設施整理的候補如下（提案），作者可以增刪、改格子：

   | 原版類別 | 候補人物 |
   | --- | --- |
   | 一般人物 N01～N10 | 觀光客（背包客）、滑雪客（北部雪國）、海灘遊客（南方離島）、拉行李箱的旅客、通勤的上班族、高中生（制服）、老人、咖啡店店員、便利商店店員、飯店櫃台人員 |
   | 科學家 N11～N20 | 醫師、護理師、藥劑師、Asuka Inc. 研發中心的研究員、氣象局的預報員、海生館的研究員；N19 放晶圓廠無塵衣（原版也是防護衣）；N20 放 Asuka Inc. 的機器人 |
   | 養蜂人 N21～N25 | 消防員、救護員、潛水員（海生館、海中公園）；N25 放吉祥物 |
   | 老師 N26～N30 | 老師、大學教授、高中生（另一款）、圖書館員、美術館的導覽員 |
   | 建築工人 N31～N35 | 工地工人（Asuka Inc. 的工地）、工地主任、機場地勤（指揮飛機）、鐵路維修員、清潔人員 |
   | 農業 N36～N45 | 農民、牧場、漁民（茉波城市漁港）、魚市場攤販、皇居離宮的庭師、蔬果攤販、造船廠工人；N39 維持稻草人（原版就是稻草人） |
   | 生物造型 N46～N50 | Minecraft Studio 的玩偶裝（樂園的工作人員），原味版一樣是動物頭 |
   | 上班族 N51～N55 | 站務員、機師、空服員、警察、黒潮特快的移民官；N52 原版是飲水機，改放自動販賣機 |
   | 服務台 N56～N60 | 機場的自助報到機（出發層的自助機台區）、車站的旅客服務機、數位導覽看板、Asuka Inc. 總部一樓的接待機、展覽中心的導覽機。NPC 可以設定對話與按鈕，點了就能顯示航班、路線之類的資訊 |

   - 還沒放進去的候補：自衛隊員、郵差、公車司機、列車長、廚師、Asuka Inc. 的警衛
   - 上班族只有 4 格是人，制服職業又多，放不下的建議放在一般人物或老師（原味版會顯示成便服的人，至少還是人）
2. **要不要做具名的人物**：例如総督、總理、Asuka Inc. 的高層、作者操控的國家領導人（[世界觀總覽](world/overview.md)裡還是待補）。具名人物用掉一格就少一種職業
3. **鼻子**：原版的人物都有村民那種鼻子。保留比較像原版 NPC；畫成透明就是一般的臉，見 `scene.png` 右下的比較。無塵衣這類戴口罩的人物一律不畫鼻子
4. **Asuka Air 的制服顏色**：品牌色還沒有設定，草稿暫用藍綠色配珊瑚色（南方島國的海）。機師用黑色制服加金線，是航空業的慣例
5. **沿用原版的模型**（Claude 建議）：見上面的 [NPC 的模型](#npc-的模型已查證2026-11-01)
6. **編號順序**：照原版資源包裡皮膚的排列，NPC 設定畫面的實際順序待實測
