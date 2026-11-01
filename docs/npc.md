# NPC 清單（皮膚的替換表）

把原版 NPC 的皮膚換成世界裡的人物時用的填空表。每一列是一個可以替換的皮膚，「人物」欄留給作者填。做法見[附加內容開發](addon.md)的 NPC 皮膚。

> 原版皮膚的對照圖用 `python3 addon/drafts/npc/vanilla_sheet.py` 產生（存到 `.scratch/npc_vanilla.png`，是 Mojang 的圖，不放進 repo）。編號照 NPC 設定畫面裡皮膚的順序（待實測）。

---

## 用法

- 原版 NPC 用 `/summon npc` 或 NPC 生成蛋放置，在 NPC 的設定畫面選皮膚、設定名字與對話；NPC 不會走動
- 資源包只換皮膚的圖，NPC 本身是原版的，所以拔掉附加內容後，NPC 還在，只是顯示原版的皮膚
- **按職業對應替換**（Claude 提案，待決定）：把世界裡的人物放在原版同一類的格子，例如站務員放在上班族、工人放在建築工人，原味版也還是同一種職業；N46～N50、N56～N60 是生物造型與機器人，拿來當一般人的話，原味版會變成非人類
- 皮膚是 64 × 64 的玩家皮膚格式

---

## 一般人物（npc_1 ～ npc_10）

原版的樣子：各種穿便服的一般人。適合：一般市民、乘客、遊客、路人。

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

原版的樣子：大多穿白色實驗衣；N19 是黃色防護衣，N20 是機器人。適合：醫師、護理師、研究員、藥局；N20 適合機器人。

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
| N19 | scientist_9 | `textures/entity/npc/npc_scientist_9.png` | | |
| N20 | scientist_10 | `textures/entity/npc/npc_scientist_10.png` | | |

## 養蜂人（npc_apiary_1 ～ 5）

原版的樣子：養蜂的人，有的戴防護面罩或穿蜜蜂裝。適合：防護裝備的工作人員、吉祥物。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N21 | apiary_1 | `textures/entity/npc/npc_apiary_1.png` | | |
| N22 | apiary_2 | `textures/entity/npc/npc_apiary_2.png` | | |
| N23 | apiary_3 | `textures/entity/npc/npc_apiary_3.png` | | |
| N24 | apiary_4 | `textures/entity/npc/npc_apiary_4.png` | | |
| N25 | apiary_5 | `textures/entity/npc/npc_apiary_5.png` | | |

## 老師（npc_teacher_1 ～ 5）

原版的樣子：老師。適合：老師、學生、教授。

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

原版的樣子：農夫、園丁，工作服居多。適合：農民、市場攤販、園丁、漁民。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N36 | Agriculture_1 | `textures/entity/npc/npc_Agriculture_1.png` | | |
| N37 | Agriculture_2 | `textures/entity/npc/npc_Agriculture_2.png` | | |
| N38 | Agriculture_3 | `textures/entity/npc/npc_Agriculture_3.png` | | |
| N39 | Agriculture_4 | `textures/entity/npc/npc_Agriculture_4.png` | | |
| N40 | Agriculture_5 | `textures/entity/npc/npc_Agriculture_5.png` | | |
| N41 | Agriculture_6 | `textures/entity/npc/npc_Agriculture_6.png` | | |
| N42 | Agriculture_7 | `textures/entity/npc/npc_Agriculture_7.png` | | |
| N43 | Agriculture_8 | `textures/entity/npc/npc_Agriculture_8.png` | | |
| N44 | Agriculture_9 | `textures/entity/npc/npc_Agriculture_9.png` | | |
| N45 | Agriculture_10 | `textures/entity/npc/npc_Agriculture_10.png` | | |

## 生物造型的商人（npc_BusinessMobs_1 ～ 5）

原版的樣子：穿衣服的生物造型角色，不是人類。適合：吉祥物、玩偶裝；拿來當一般人的話，原味版會變成生物造型。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N46 | BusinessMobs_1 | `textures/entity/npc/npc_BusinessMobs_1.png` | | |
| N47 | BusinessMobs_2 | `textures/entity/npc/npc_BusinessMobs_2.png` | | |
| N48 | BusinessMobs_3 | `textures/entity/npc/npc_BusinessMobs_3.png` | | |
| N49 | BusinessMobs_4 | `textures/entity/npc/npc_BusinessMobs_4.png` | | |
| N50 | BusinessMobs_5 | `textures/entity/npc/npc_BusinessMobs_5.png` | | |

## 上班族（npc_EverydayBusiness_1 ～ 5）

原版的樣子：襯衫、西裝等上班族。適合：站務員、空服員、櫃台人員、店員、公務員。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N51 | EverydayBusiness_1 | `textures/entity/npc/npc_EverydayBusiness_1.png` | | |
| N52 | EverydayBusiness_2 | `textures/entity/npc/npc_EverydayBusiness_2.png` | | |
| N53 | EverydayBusiness_3 | `textures/entity/npc/npc_EverydayBusiness_3.png` | | |
| N54 | EverydayBusiness_4 | `textures/entity/npc/npc_EverydayBusiness_4.png` | | |
| N55 | EverydayBusiness_5 | `textures/entity/npc/npc_EverydayBusiness_5.png` | | |

## 服務台（npc_Kiosk_1 ～ 5）

原版的樣子：機器人、吉祥物造型。適合：導覽機器人、吉祥物。

| 編號 | 原版皮膚 | 檔案 | 人物 | 備註 |
| --- | --- | --- | --- | --- |
| N56 | Kiosk_1 | `textures/entity/npc/npc_Kiosk_1.png` | | |
| N57 | Kiosk_2 | `textures/entity/npc/npc_Kiosk_2.png` | | |
| N58 | Kiosk_3 | `textures/entity/npc/npc_Kiosk_3.png` | | |
| N59 | Kiosk_4 | `textures/entity/npc/npc_Kiosk_4.png` | | |
| N60 | Kiosk_5 | `textures/entity/npc/npc_Kiosk_5.png` | | |
