// 物品收藏：把染好色、印好圖案的旗幟、盾牌（或任何物品）存起來，之後隨時拿出一份。
//
// 做法和結構方塊一樣：在玩家頭頂的高空暫時放一個箱子，把物品放進去，
// 用 structureManager 把這個箱子存成世界裡的結構（asuka:fav_xxxx），再把物品拿回來、把箱子移掉。
// 拿取時把結構放回高空，從箱子裡拿出物品，再把箱子移掉。
// 結構是原版資料，拔掉行為包後也可以用 /structure load asuka:fav_xxxx ~ ~ ~ 叫出裝著物品的箱子。

import { world, StructureSaveMode } from '@minecraft/server';
import { ActionFormData, ModalFormData } from '@minecraft/server-ui';
import { notify, showForm, inventoryOf } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {import('@minecraft/server').Block} Block */
/** @typedef {import('@minecraft/server').Dimension} Dimension */
/** @typedef {(player: Player) => Promise<void>} Back */

/**
 * @typedef {object} Favorite
 * @property {string} key 結構名稱
 * @property {string} name 顯示名稱
 * @property {string} typeId 物品 ID
 * @property {number} amount 數量
 */

/** 收藏清單存在世界的 dynamic property */
const LIST_KEY = 'asuka:favorites';
/** 暫時放箱子的位置：從世界頂端往下找空氣，最多找幾格 */
const SCRATCH_SEARCH_DEPTH = 48;

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
 * 在玩家頭頂高空找一格空氣，暫時放箱子用。
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

/**
 * @param {Block} block
 */
function chestContainer(block) {
  return block.getComponent('minecraft:inventory')?.container;
}

/**
 * 把手上的物品存成收藏。
 * @param {Player} player
 * @param {string} name
 * @returns {Favorite | undefined}
 */
function saveHeldItem(player, name) {
  const inventory = inventoryOf(player);
  const slot = player.selectedSlotIndex;
  const item = inventory.getItem(slot);
  if (!item) {
    notify(player, '§c手上沒有拿東西');
    return undefined;
  }
  const scratch = findScratchBlock(player);
  if (!scratch) {
    notify(player, '§c頭頂上方找不到空位，換個地方再試');
    return undefined;
  }

  const key = `asuka:fav_${Date.now().toString(36)}`;
  const location = scratch.location;
  scratch.setType('minecraft:chest');
  const chest = chestContainer(scratch);
  if (!chest) {
    scratch.setType('minecraft:air');
    notify(player, '§c暫存用的箱子放不出來');
    return undefined;
  }

  const favorite = { key, name, typeId: item.typeId, amount: item.amount };
  // 用 moveItem 搬動遊戲內部的物品資料，旗幟圖案、附魔、名稱等全部原封不動
  inventory.moveItem(slot, 0, chest);
  try {
    world.structureManager.createFromWorld(key, player.dimension, location, location, {
      includeBlocks: true,
      includeEntities: false,
      saveMode: StructureSaveMode.World,
    });
  } finally {
    chest.moveItem(0, slot, inventory);
    chest.clearAll();
    scratch.setType('minecraft:air');
  }
  return favorite;
}

/**
 * 從收藏拿出一份放進背包。
 * @param {Player} player
 * @param {Favorite} favorite
 */
function takeFavorite(player, favorite) {
  if (!world.structureManager.get(favorite.key)) {
    notify(player, `§c找不到「${favorite.name}」的結構（${favorite.key}），可能被刪掉了`);
    return;
  }
  const inventory = inventoryOf(player);
  if (inventory.emptySlotsCount === 0) {
    notify(player, '§c背包滿了，先空出一格');
    return;
  }
  const scratch = findScratchBlock(player);
  if (!scratch) {
    notify(player, '§c頭頂上方找不到空位，換個地方再試');
    return;
  }
  const location = scratch.location;
  const dimension = player.dimension;
  world.structureManager.place(favorite.key, dimension, location, { includeEntities: false });
  const placed = dimension.getBlock(location);
  try {
    const chest = placed ? chestContainer(placed) : undefined;
    const slot = chest?.firstItem();
    if (!chest || slot === undefined) {
      notify(player, `§c「${favorite.name}」的結構裡沒有東西`);
      return;
    }
    chest.transferItem(slot, inventory);
    notify(player, `§a拿到「${favorite.name}」`);
  } finally {
    if (placed) {
      chestContainer(placed)?.clearAll();
      placed.setType('minecraft:air');
    }
  }
}

// ---------------------------------------------------------------------------
// 選單
// ---------------------------------------------------------------------------

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openSaveForm(player, back) {
  const item = inventoryOf(player).getItem(player.selectedSlotIndex);
  if (!item) {
    notify(player, '§c先把要收藏的物品拿在手上');
    return back(player);
  }
  const form = new ModalFormData()
    .title('收藏手上的物品')
    .textField(`名稱（${shortId(item.typeId)} × ${item.amount}）`, '例如 津蘭國旗', {
      defaultValue: item.nameTag ?? '',
    })
    .submitButton('收藏');
  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return back(player);
  const name = String(response.formValues[0] ?? '').trim() || shortId(item.typeId);
  const favorite = saveHeldItem(player, name);
  if (!favorite) return;
  const list = loadFavorites();
  list.push(favorite);
  saveFavorites(list);
  notify(player, `§a已收藏「${name}」`);
}

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openManage(player, back) {
  const list = loadFavorites();
  if (list.length === 0) return back(player);
  const form = new ActionFormData().title('管理收藏').body('選擇要改名或刪除的收藏。');
  for (const f of list) form.button(`${f.name}\n§8${shortId(f.typeId)} × ${f.amount}`);
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const favorite = list[response.selection];
  if (!favorite) return back(player);

  const action = await showForm(
    player,
    new ActionFormData()
      .title(favorite.name)
      .body(`結構名稱：${favorite.key}`)
      .button('改名')
      .button('§c刪除')
      .button('返回'),
  );
  if (!action || action.canceled) return;
  if (action.selection === 0) {
    const rename = await showForm(
      player,
      new ModalFormData()
        .title('改名')
        .textField('新的名稱', favorite.name, { defaultValue: favorite.name })
        .submitButton('儲存'),
    );
    const name = String(rename?.formValues?.[0] ?? '').trim();
    if (rename && !rename.canceled && name) {
      const next = loadFavorites().map((f) => (f.key === favorite.key ? { ...f, name } : f));
      saveFavorites(next);
      notify(player, `§a已改名為「${name}」`);
    }
  } else if (action.selection === 1) {
    const confirm = await showForm(
      player,
      new ActionFormData()
        .title('確定要刪除？')
        .body(`「${favorite.name}」會從收藏和世界的結構裡一起刪掉，無法復原。`)
        .button('§c刪除')
        .button('取消'),
    );
    if (confirm && !confirm.canceled && confirm.selection === 0) {
      world.structureManager.delete(favorite.key);
      saveFavorites(loadFavorites().filter((f) => f.key !== favorite.key));
      notify(player, `§7已刪除「${favorite.name}」`);
    }
  }
  await openManage(player, back);
}

/**
 * @param {Player} player
 * @param {Back} [onBack]
 */
export async function openFavoritesMenu(player, onBack) {
  const self = () => openFavoritesMenu(player, onBack);
  const list = loadFavorites();
  const form = new ActionFormData()
    .title('物品收藏')
    .body(
      list.length > 0
        ? '按一下就拿出一份，收藏本身不會減少。'
        : '還沒有收藏。把染好的旗幟、盾牌拿在手上，按「收藏手上的物品」。',
    )
    .button('§2收藏手上的物品');
  for (const f of list) form.button(`${f.name}\n§8${shortId(f.typeId)} × ${f.amount}`);
  form.button('管理（改名、刪除）');
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const i = response.selection;
  if (i === 0) await openSaveForm(player, self);
  else if (i <= list.length) takeFavorite(player, list[i - 1]);
  else if (i === list.length + 1) await openManage(player, self);
  else if (onBack) await onBack(player);
}
