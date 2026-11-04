// 物品收藏（烈焰棒）：把旗幟、盾牌等東西存起來，之後隨時拿出一份。
//
// 操作：
//   揮一下或右鍵           → 開收藏清單，按一下就拿
//   蹲下右鍵點方塊         → 收藏那個方塊；點物品框架就收藏框架裡的物品
//   蹲下對空氣右鍵         → 收藏快捷列裡烈焰棒右邊那一格的物品
//
// 手上拿著烈焰棒，所以沒辦法收藏手上的東西。
//
// 做法和結構方塊一樣：在玩家頭頂的高空暫時放一個箱子，把物品放進去，
// 用 structureManager 把這個箱子存成世界裡的結構（asuka:fav_xxxx），再把箱子移掉。
// 拿取時把結構放回高空，從箱子裡拿出物品，再把箱子移掉。
// 結構是原版資料，拔掉行為包後也可以用 /structure load asuka:fav_xxxx ~ ~ ~ 叫出裝著物品的箱子。
//
// 收藏方塊時，先在高空放一份複製品再打掉，把掉落物放進箱子：這樣收藏當下就知道拿不拿得回來
// （玻璃這種打掉不掉東西的會直接說不行），世界裡原本的方塊也不會動到。

import { world, StructureSaveMode } from '@minecraft/server';
import { ActionFormData } from '@minecraft/server-ui';
import { notify, showForm, showWarning, inventoryOf, waitTicks } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {import('@minecraft/server').Block} Block */
/** @typedef {import('@minecraft/server').Container} Container */
/** @typedef {import('@minecraft/server').ItemStack} ItemStack */

/**
 * @typedef {object} Favorite
 * @property {string} key 結構名稱
 * @property {string} typeId 物品 ID
 * @property {number} amount 數量
 * @property {string} [nameKey] 物品的遊戲內名稱（翻譯鍵）
 * @property {string} [name] 物品自己的名字（鐵砧改過的），或舊版收藏取的名字
 * @property {number} [number] 同一種物品的第幾個，沒有改名時用來分辨
 */

/** 收藏清單存在世界的 dynamic property */
const LIST_KEY = 'asuka:favorites';
/** 暫時放箱子的位置：從世界頂端往下找空氣，最多找幾格 */
const SCRATCH_SEARCH_DEPTH = 48;
/** 快捷列有 9 格 */
const HOTBAR_SIZE = 9;
/** 收藏物品框架時，框架本身不算 */
const FRAME_TYPES = new Set(['minecraft:frame', 'minecraft:glow_frame']);

/** @returns {Favorite[]} */
function loadFavorites() {
  try {
    const raw = world.getDynamicProperty(LIST_KEY);
    if (typeof raw === 'string') {
      const list = JSON.parse(raw);
      if (Array.isArray(list)) return list.filter((f) => typeof f?.key === 'string');
    }
  } catch {
    // 壞掉就當作空的
  }
  return [];
}

/** @param {Favorite[]} list */
function saveFavorites(list) {
  world.setDynamicProperty(LIST_KEY, JSON.stringify(list));
}

/** @param {string} typeId */
function shortId(typeId) {
  return typeId.replace(/^minecraft:/, '');
}

/**
 * 物品的顯示名稱；旗幟這種同名的東西，用編號分辨。
 * @param {Favorite} f
 * @returns {import('@minecraft/server').RawMessage}
 */
function nameOf(f) {
  const name = f.name || !f.nameKey ? { text: f.name ?? shortId(f.typeId) } : { translate: f.nameKey };
  return { rawtext: [name, { text: (f.number ?? 1) > 1 ? ` #${f.number}` : '' }] };
}

/**
 * @param {Favorite} f
 * @returns {import('@minecraft/server').RawMessage}
 */
function buttonLabel(f) {
  return { rawtext: [nameOf(f), { text: `\n§8${shortId(f.typeId)} × ${f.amount}` }] };
}

/**
 * 在玩家頭頂高空找一格空氣，暫時放東西用。
 * @param {Player} player
 * @returns {Block | undefined}
 */
function findScratchBlock(player) {
  const dimension = player.dimension;
  const { min, max } = dimension.heightRange;
  const x = Math.floor(player.location.x);
  const z = Math.floor(player.location.z);
  const playerY = Math.floor(player.location.y);
  for (let y = max - 1; y >= Math.max(min, max - SCRATCH_SEARCH_DEPTH); y--) {
    if (Math.abs(y - playerY) <= 3) continue; // 不要放在玩家身邊
    let block;
    try {
      block = dimension.getBlock({ x, y, z });
    } catch {
      block = undefined;
    }
    if (block?.isAir) return block;
  }
  return undefined;
}

/** @param {Block} block */
function chestContainer(block) {
  return block.getComponent('minecraft:inventory')?.container;
}

/**
 * 加進收藏清單，並告訴玩家。
 * @param {Player} player
 * @param {{ key: string, item: ItemStack }} saved
 */
function remember(player, { key, item }) {
  const list = loadFavorites();
  const number = list.filter((f) => f.typeId === item.typeId).length + 1;
  /** @type {Favorite} */
  const favorite = { key, typeId: item.typeId, amount: item.amount, nameKey: item.localizationKey, number };
  if (item.nameTag) favorite.name = item.nameTag;
  list.push(favorite);
  saveFavorites(list);
  notify(player, { rawtext: [{ text: '§a已收藏 ' }, nameOf(favorite)] });
}

/**
 * 把暫存箱子存成結構。
 * @param {Player} player
 * @param {Block} chestBlock
 */
function saveChestAsStructure(player, chestBlock) {
  const key = `asuka:fav_${Date.now().toString(36)}`;
  const location = chestBlock.location;
  world.structureManager.createFromWorld(key, player.dimension, location, location, {
    includeBlocks: true,
    includeEntities: false,
    saveMode: StructureSaveMode.World,
  });
  return key;
}

/**
 * 收藏快捷列裡烈焰棒右邊那一格的物品；物品留在原位。
 * @param {Player} player
 */
export function saveRightSlot(player) {
  const inventory = inventoryOf(player);
  const slot = player.selectedSlotIndex + 1;
  const item = slot < HOTBAR_SIZE ? inventory.getItem(slot) : undefined;
  if (slot >= HOTBAR_SIZE) {
    notify(player, '§c烈焰棒在快捷列最右邊，右邊沒有格子');
    return;
  }
  if (!item) {
    notify(player, '§c烈焰棒右邊那一格是空的');
    return;
  }
  const scratch = findScratchBlock(player);
  if (!scratch) {
    notify(player, '§c頭頂上方找不到空位，換個地方再試');
    return;
  }
  scratch.setType('minecraft:chest');
  const chest = chestContainer(scratch);
  if (!chest) {
    scratch.setType('minecraft:air');
    notify(player, '§c暫存用的箱子放不出來');
    return;
  }
  // 用 moveItem 搬動遊戲內部的物品資料，旗幟圖案、附魔、名稱等全部原封不動
  inventory.moveItem(slot, 0, chest);
  try {
    remember(player, { key: saveChestAsStructure(player, scratch), item });
  } finally {
    chest.moveItem(0, slot, inventory);
    chest.clearAll();
    scratch.setType('minecraft:air');
  }
}

/**
 * 收藏世界裡的方塊；物品框架就收藏框架裡的物品。原本的方塊不會動到。
 * @param {Player} player
 * @param {Block} block
 */
export async function saveFromBlock(player, block) {
  const dimension = player.dimension;
  const scratch = findScratchBlock(player);
  if (!scratch) {
    notify(player, '§c頭頂上方找不到空位，換個地方再試');
    return;
  }
  const isFrame = FRAME_TYPES.has(block.typeId);
  const from = block.location;
  const at = scratch.location;

  // 在高空放一份複製品再打掉
  const tempKey = `asuka:tmp_${Date.now().toString(36)}`;
  world.structureManager.createFromWorld(tempKey, dimension, from, from, {
    includeBlocks: true,
    includeEntities: false,
    saveMode: StructureSaveMode.Memory,
  });
  try {
    world.structureManager.place(tempKey, dimension, at, { includeEntities: false });
  } finally {
    world.structureManager.delete(tempKey);
  }
  dimension.runCommand(`setblock ${at.x} ${at.y} ${at.z} air destroy`);
  await waitTicks(2);

  const drops = dimension.getEntities({
    type: 'minecraft:item',
    location: { x: at.x + 0.5, y: at.y + 0.5, z: at.z + 0.5 },
    maxDistance: 4,
  });
  /** @type {ItemStack[]} */
  const items = [];
  for (const drop of drops) {
    const item = drop.getComponent('minecraft:item')?.itemStack;
    if (item && !(isFrame && FRAME_TYPES.has(item.typeId))) items.push(item);
    drop.remove();
  }
  if (items.length === 0) {
    notify(player, isFrame ? '§c這個框架裡沒有東西' : '§c這個方塊打掉不會掉東西，沒辦法收藏');
    return;
  }

  const spot = dimension.getBlock(at);
  if (!spot) return;
  spot.setType('minecraft:chest');
  try {
    const chest = chestContainer(spot);
    if (!chest) {
      notify(player, '§c暫存用的箱子放不出來');
      return;
    }
    items.slice(0, chest.size).forEach((item, slot) => chest.setItem(slot, item));
    remember(player, { key: saveChestAsStructure(player, spot), item: items[0] });
    chest.clearAll();
  } finally {
    spot.setType('minecraft:air');
  }
}

/**
 * 從收藏拿出一份放進包包。
 * @param {Player} player
 * @param {Favorite} favorite
 * @returns {boolean} 包包有沒有放得下
 */
function takeFavorite(player, favorite) {
  if (!world.structureManager.get(favorite.key)) {
    notify(player, { rawtext: [{ text: '§c找不到這個收藏的結構，可能被刪掉了：' }, nameOf(favorite)] });
    return true;
  }
  const inventory = inventoryOf(player);
  if (inventory.emptySlotsCount === 0) return false;
  const scratch = findScratchBlock(player);
  if (!scratch) {
    notify(player, '§c頭頂上方找不到空位，換個地方再試');
    return true;
  }
  const location = scratch.location;
  const dimension = player.dimension;
  world.structureManager.place(favorite.key, dimension, location, { includeEntities: false });
  const placed = dimension.getBlock(location);
  try {
    const chest = placed ? chestContainer(placed) : undefined;
    if (!chest) return true;
    let slot = chest.firstItem();
    if (slot === undefined) {
      notify(player, { rawtext: [{ text: '§c這個收藏的結構裡沒有東西：' }, nameOf(favorite)] });
      return true;
    }
    while (slot !== undefined) {
      if (chest.transferItem(slot, inventory)) return false; // 還有放不下的
      slot = chest.firstItem();
    }
    notify(player, { rawtext: [{ text: '§a拿到 ' }, nameOf(favorite)] });
    return true;
  } finally {
    if (placed) {
      chestContainer(placed)?.clearAll();
      placed.setType('minecraft:air');
    }
  }
}

/**
 * 管理收藏：只有刪除（作者不要改名，2026-11-05）。
 * @param {Player} player
 */
async function openManage(player) {
  for (;;) {
    const list = loadFavorites();
    if (list.length === 0) return;
    const form = new ActionFormData().title('刪除收藏').body('選擇要刪除的收藏。按 X 回上一頁。');
    for (const f of list) form.button(buttonLabel(f));
    const response = await showForm(player, form);
    if (!response || response.canceled || response.selection === undefined) return;

    const favorite = list[response.selection];
    const confirm = await showForm(
      player,
      new ActionFormData()
        .title('確定要刪除？')
        .body({ rawtext: [{ text: '會從收藏和世界的結構裡一起刪掉，無法復原：\n' }, nameOf(favorite)] })
        .button('§c刪除')
        .button('取消'),
    );
    if (confirm && !confirm.canceled && confirm.selection === 0) {
      saveFavorites(list.filter((f) => f.key !== favorite.key));
      world.structureManager.delete(favorite.key);
    }
  }
}

/**
 * 收藏清單。按完不關頁面：連續拿好幾樣不用重開（遊戲的表單按了就關，所以是馬上重開同一頁）。
 * @param {Player} player
 */
export async function openFavorites(player) {
  for (;;) {
    const list = loadFavorites();
    const form = new ActionFormData()
      .title('物品收藏')
      .body(list.length > 0 ? '按一下就拿一份，收藏本身不會減少。' : '還沒有收藏。\n拿烈焰棒蹲下右鍵點旗幟、物品框架或其他方塊就能收藏；蹲下對空氣右鍵可以收藏右邊那一格的物品。');
    for (const f of list) form.button(buttonLabel(f));
    if (list.length > 0) form.button('刪除收藏');

    const response = await showForm(player, form);
    if (!response || response.canceled || response.selection === undefined) return;
    if (response.selection === list.length) {
      await openManage(player);
    } else if (!takeFavorite(player, list[response.selection])) {
      await showWarning(player, '包包滿了', '放不下，先空出一格再拿。');
    }
  }
}
