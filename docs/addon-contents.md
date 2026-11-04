# 附加內容清單

自製附加內容 Asuka tech 目前做了哪些東西，分成四類，方便清點與調閱。做法、討論與實測紀錄在[附加內容開發](addon.md)。

> **維護規則（作者要求，2026-11-04）**：之後每新增、修改或拿掉一樣東西，都要同時更新這份清單（類別、加入的版本、草稿位置），和 `docs/addon.md` 的版本紀錄一起 commit。

目前版本：**v0.7.6**（2026-11-05）。「加入」欄是第一次放進附加內容的版本，後面括號是之後改過外觀的版本。

## 一、直接改材質

只換原版東西的外觀，拔掉資源包就回到原版，原味版不用轉換。

| 原版 | 改成 | 加入 | 草稿 |
| --- | --- | --- | --- |
| 畫 | 37 幅廣告；一格大小的 2 幅改成筆電螢幕（桌面、寫程式）；所有畫的背面改成灰色筆電上蓋 | v0.1.0（v0.7.6 加上地鐵路線圖） | `addon/drafts/ads/`、`addon/drafts/laptop/` |
| 物品框架 | 白色展示框，兼當萬用盤子（只換中間的底，木框不變） | v0.1.0 | `addon/drafts/white_frame/` |
| 發光物品框架 | 萬用小螢幕（只換中間，木框不變） | v0.1.0 | `addon/drafts/screen/` |
| 白色界伏蚌盒 | 鐵製置物櫃 | v0.1.0 | `addon/drafts/locker/` |
| 淺灰色界伏蚌盒 | 辦公室抽屜櫃 | v0.5.0 | `addon/drafts/drawer/` |
| 漏斗 | 小便斗 | v0.1.0 | `addon/drafts/hopper/` |
| 坐墊（16 色） | 拿掉中間的釦子 | v0.5.0 | `addon/drafts/props/` |
| 花盆 | 深灰色（方塊與物品圖示） | v0.5.0（v0.5.1 改深灰） | `addon/drafts/props/` |
| 陶罐 | 白鐵罐，加深灰色瓶蓋 | v0.5.0 | `addon/drafts/props/` |
| 凋零骷髏頭 | 沒有臉，四面一樣 | v0.5.0 | `addon/drafts/props/` |
| 蒼白橡木展示架 | 鐵製貨架（三個小掛勾） | v0.5.0 | `addon/drafts/props/` |
| 儲物箱（含大箱子） | 鋁製行李箱（內側是深藍色內襯）；物品欄圖示維持原版 | v0.5.0（v0.5.1 補內側） | `addon/drafts/suitcase/` |
| 海鞘 | 淺灰色鐵杯（物品圖示是立體的） | v0.5.0（v0.5.1 改淺灰） | `addon/drafts/cup/` |
| 釀造台 | 手沖咖啡架（物品圖示是吊著咖啡壺的架子） | v0.6.0 | `addon/drafts/coffee_machine/` |
| 終界燭 | 不顯示粒子效果（改粒子檔，不是材質） | v0.1.0 | — |

## 二、只改圖示與名稱

物品拿在手上、放進展示框或展示架時的樣子；放在世界裡的東西不變。

| 原版 | 改成 | 加入 | 草稿 |
| --- | --- | --- | --- |
| 牛奶桶 | 瓶裝牛奶（淺灰色瓶蓋） | v0.5.0（v0.7.2 改瓶裝） | `addon/drafts/props/` |
| 20 種藥水 | 20 種飲料，圖示與名稱都改（對照表在 [addon.md](addon.md#44-第二批構想2026-11-03)） | v0.5.0 | `addon/drafts/drinks/` |

## 三、新增的方塊

原版沒有的方塊。原味版由轉換程式照 `addon/mapping.json` 換成原版方塊。

| 方塊 | 識別碼 | 原味版 | 加入 | 草稿 |
| --- | --- | --- | --- | --- |
| 白色門、淺灰色門 | `asukatech:door_white`、`door_light_gray` | 杉木門 | v0.1.0 | `addon/drafts/doors/` |
| 白色地板門、淺灰色地板門 | `asukatech:trapdoor_white`、`trapdoor_light_gray` | 杉木地板門 | v0.1.0 | `addon/drafts/doors/` |
| 外帶咖啡杯（1～4 杯） | `asukatech:coffee_cup` | 空氣（不顯示） | v0.1.0 | `addon/drafts/coffee_cup/` |
| 八角形玻璃水杯（1～4 杯） | `asukatech:glass_cup` | 海鞘（同樣個數） | v0.7.0 | `addon/drafts/glass_cup/` |
| 小螢幕（會發光） | `asukatech:screen` | 空的發光物品框架 | v0.5.0 | `addon/drafts/screen_block/` |

共 7 種。門與小螢幕另有同名的物品取代方塊的物品，物品欄才會顯示正確的圖示（v0.7.1、v0.7.3）。

## 四、新增的實體

原版沒有的實體，拔掉附加內容或轉成原味版時直接消失（作者接受，2026-11-03）。都用物品放下、打一下收回。

| 實體 | 識別碼 | 數量 | 加入 | 草稿 |
| --- | --- | --- | --- | --- |
| 餐具：白盤子、白碗、白杯子、餐刀、叉子、湯匙、筷子 | `asukatech:plate`、`bowl`、`cup`、`knife`、`fork`、`spoon`、`chopsticks` | 7 | v0.5.0 | `addon/drafts/tableware/` |
| iPad | `asukatech:ipad` | 1 | v0.7.0 | `addon/drafts/ipad/` |
| 直立的行李箱：深藍色登機箱、紅色大行李箱、鋁製、黑色布面、粉色 | `asukatech:suitcase_<種類>` | 5 | v0.6.0 | `addon/drafts/suitcases/` |
| 行李礦車（躺在鐵軌上，各對應一種行李箱） | `asukatech:luggage_cart_<種類>` | 5 | v0.6.0 | `addon/drafts/suitcases/` |

共 18 種。種類是 `cabin_navy`、`large_red`、`aluminium`、`soft_black`、`pink`。每種餐具與 iPad 各一個同名的物品；每種行李箱一個物品 `asukatech:suitcase_<種類>`，點在鐵軌上放行李礦車，點在其他方塊上面放直立的行李箱。

## 其他

| 項目 | 內容 | 加入 |
| --- | --- | --- |
| 物品欄分類 | 「物品」分頁：餐具、行李箱、杯子（咖啡紙杯、玻璃水杯）；「建築」分頁：門、地板門 | v0.7.1（門 v0.7.4、地板門 v0.7.5） |
| Rail to Belt | 另一個獨立的材質包，把所有鐵軌換成履帶，不在 Asuka tech 裡（見 [addon.md](addon.md#52-rail-to-belt)） | v1.0.0 |
| Asuka 工具包 | 另一個獨立的行為包，只有腳本，不在 Asuka tech 裡，也不會併進來（見 [addon.md](addon.md#53-asuka-工具包)） | v2.0.0（目前 v2.0.2） |
