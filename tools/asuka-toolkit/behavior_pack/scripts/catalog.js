// 常用物品清單：創造模式物品欄裡沒有、平常要用 /give 才拿得到的東西。
// 純資料，不依賴 @minecraft/server。要加東西直接改這裡。

/**
 * @typedef {object} CatalogItem
 * @property {string} id 物品 ID
 * @property {string} label 顯示名稱
 * @property {number} amount 按一下給幾個
 */

/**
 * @typedef {object} CatalogCategory
 * @property {string} id
 * @property {string} label
 * @property {CatalogItem[]} items
 */

/** @type {CatalogCategory[]} */
export const CATEGORIES = [
  {
    id: 'building',
    label: '建造輔助',
    items: [
      { id: 'minecraft:structure_block', label: '結構方塊', amount: 1 },
      { id: 'minecraft:structure_void', label: '結構空位', amount: 64 },
      { id: 'minecraft:barrier', label: '屏障', amount: 64 },
      { id: 'minecraft:border_block', label: '邊界', amount: 64 },
      { id: 'minecraft:allow', label: '允許方塊', amount: 64 },
      { id: 'minecraft:deny', label: '拒絕方塊', amount: 64 },
      { id: 'minecraft:jigsaw', label: '拼圖方塊', amount: 1 },
    ],
  },
  {
    id: 'command',
    label: '指令方塊',
    items: [
      { id: 'minecraft:command_block', label: '指令方塊', amount: 1 },
      { id: 'minecraft:repeating_command_block', label: '重複指令方塊', amount: 1 },
      { id: 'minecraft:chain_command_block', label: '連鎖指令方塊', amount: 1 },
      { id: 'minecraft:command_block_minecart', label: '指令方塊礦車', amount: 1 },
    ],
  },
  {
    id: 'special',
    label: '特殊方塊',
    items: [
      { id: 'minecraft:mob_spawner', label: '生怪磚', amount: 1 },
      { id: 'minecraft:trial_spawner', label: '試煉生怪磚', amount: 1 },
      { id: 'minecraft:vault', label: '寶庫', amount: 1 },
      { id: 'minecraft:petrified_oak_slab', label: '石化橡木半磚', amount: 64 },
      { id: 'minecraft:frosted_ice', label: '霜冰', amount: 64 },
    ],
  },
  {
    id: 'eggs',
    label: '生怪蛋',
    items: [
      { id: 'minecraft:iron_golem_spawn_egg', label: '鐵魔像生怪蛋', amount: 1 },
      { id: 'minecraft:snow_golem_spawn_egg', label: '雪人生怪蛋', amount: 1 },
      { id: 'minecraft:wither_spawn_egg', label: '凋零怪生怪蛋', amount: 1 },
      { id: 'minecraft:ender_dragon_spawn_egg', label: '終界龍生怪蛋', amount: 1 },
    ],
  },
];

/**
 * 光源方塊的物品 ID（亮度 0～15）。
 * @param {number} level
 */
export function lightBlockId(level) {
  const n = Math.min(15, Math.max(0, Math.trunc(level)));
  return `minecraft:light_block_${n}`;
}

/**
 * 使用者輸入的物品 ID：補上 minecraft: 前綴、轉小寫、去掉空白。
 * @param {string} text
 * @returns {string | undefined}
 */
export function normalizeItemId(text) {
  const id = String(text ?? '').trim().toLowerCase();
  if (!/^([a-z0-9_.-]+:)?[a-z0-9_./-]+$/.test(id)) return undefined;
  return id.includes(':') ? id : `minecraft:${id}`;
}
