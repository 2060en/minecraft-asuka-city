// 旋風棒的特殊物品清單：創造模式物品欄裡沒有、平常要用 /give 才拿得到的東西，作者選的（2026-11-05）。
// 純資料，不依賴 @minecraft/server。要加東西直接改這裡。

/**
 * @typedef {object} SpecialItem
 * @property {string} id 物品 ID
 * @property {string} label 顯示名稱
 * @property {number} amount 按一下給幾個
 */

/** @type {SpecialItem[]} */
export const SPECIAL_ITEMS = [
  { id: 'minecraft:structure_block', label: '結構方塊', amount: 1 },
  { id: 'minecraft:structure_void', label: '結構空位', amount: 64 },
  { id: 'minecraft:barrier', label: '屏障', amount: 64 },
  { id: 'minecraft:light_block_15', label: '光源方塊（亮度 15）', amount: 64 },
  { id: 'minecraft:command_block', label: '指令方塊', amount: 1 },
  { id: 'minecraft:repeating_command_block', label: '重複指令方塊', amount: 1 },
  { id: 'minecraft:chain_command_block', label: '連鎖指令方塊', amount: 1 },
];
