// 常用物品：把要用 /give 才拿得到的東西做成選單，按一下就放進背包。

import { world, ItemStack } from '@minecraft/server';
import { ActionFormData, ModalFormData } from '@minecraft/server-ui';
import { CATEGORIES, lightBlockId, normalizeItemId } from './catalog.js';
import { parseIntInRange } from './line.js';
import { notify, showForm, inventoryOf } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {(player: Player) => Promise<void>} Back */

/** 自訂清單存在世界的 dynamic property */
const CUSTOM_KEY = 'asuka:custom_items';
/** 上次選的光源亮度，存在玩家身上 */
const LIGHT_KEY = 'asuka:light_level';

/**
 * 把物品放進玩家背包，超過一組時分成好幾組。
 * @param {Player} player
 * @param {string} typeId
 * @param {number} amount
 * @param {string} label
 * @returns {boolean} 是否成功
 */
export function giveItem(player, typeId, amount, label) {
  let maxAmount;
  try {
    maxAmount = new ItemStack(typeId, 1).maxAmount;
  } catch {
    notify(player, `§c找不到物品「${typeId}」`);
    return false;
  }
  const inventory = inventoryOf(player);
  let given = 0;
  while (given < amount) {
    const n = Math.min(maxAmount, amount - given);
    const leftover = inventory.addItem(new ItemStack(typeId, n));
    given += n - (leftover?.amount ?? 0);
    if (leftover) break;
  }
  if (given === 0) {
    notify(player, '§c背包滿了');
    return false;
  }
  notify(player, `§a拿到 ${label} × ${given}${given < amount ? '§e（背包滿了，沒拿完）' : ''}`);
  return true;
}

// ---------------------------------------------------------------------------
// 自訂清單
// ---------------------------------------------------------------------------

/** @returns {{ id: string, label: string, amount: number }[]} */
function loadCustomItems() {
  try {
    const raw = world.getDynamicProperty(CUSTOM_KEY);
    if (typeof raw === 'string') {
      const list = JSON.parse(raw);
      if (Array.isArray(list)) return list.filter((i) => typeof i?.id === 'string');
    }
  } catch {
    // 壞掉就當作空的
  }
  return [];
}

/** @param {{ id: string, label: string, amount: number }[]} list */
function saveCustomItems(list) {
  world.setDynamicProperty(CUSTOM_KEY, JSON.stringify(list));
}

/**
 * 輸入任何物品 ID 拿東西，可以順便加進自訂清單。
 * @param {Player} player
 * @param {Back} back
 */
async function openCustomInput(player, back) {
  const form = new ModalFormData()
    .title('輸入物品 ID')
    .textField('物品 ID（可以省略 minecraft:）', '例如 light_block_15', { defaultValue: '' })
    .textField('數量', '例如 64', { defaultValue: '1' })
    .textField('加入自訂清單時顯示的名稱（留空就不加入）', '例如 亮度 15 的光源', { defaultValue: '' })
    .submitButton('拿取');
  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return back(player);
  const [idText, amountText, labelText] = response.formValues;
  const id = normalizeItemId(String(idText));
  if (!id) {
    notify(player, '§c物品 ID 的格式不對');
    return back(player);
  }
  const amount = parseIntInRange(amountText, 1, 64 * 36) ?? 1;
  const label = String(labelText ?? '').trim();
  const ok = giveItem(player, id, amount, label || id);
  if (ok && label) {
    const list = loadCustomItems().filter((i) => i.id !== id);
    list.push({ id, label, amount });
    saveCustomItems(list);
    player.sendMessage(`§a已把「${label}」加入自訂清單`);
  }
}

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openCustomList(player, back) {
  const list = loadCustomItems();
  const form = new ActionFormData().title('自訂清單');
  form.body(list.length > 0 ? '按一下就拿。' : '還沒有東西。用「輸入物品 ID」拿東西時填上名稱，就會加進這裡。');
  for (const item of list) form.button(`${item.label} × ${item.amount}\n§8${item.id}`);
  form.button('從清單移除…');
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const i = response.selection;
  if (i < list.length) {
    giveItem(player, list[i].id, list[i].amount, list[i].label);
  } else if (i === list.length) {
    await openRemoveCustom(player, () => openCustomList(player, back));
  } else {
    await back(player);
  }
}

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openRemoveCustom(player, back) {
  const list = loadCustomItems();
  if (list.length === 0) return back(player);
  const form = new ActionFormData().title('從自訂清單移除').body('選擇要移除的物品。');
  for (const item of list) form.button(`§c${item.label}\n§8${item.id}`);
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  if (response.selection < list.length) {
    const [removed] = list.splice(response.selection, 1);
    saveCustomItems(list);
    notify(player, `§7已移除「${removed.label}」`);
  }
  await back(player);
}

// ---------------------------------------------------------------------------
// 選單
// ---------------------------------------------------------------------------

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openLightBlock(player, back) {
  const last = player.getDynamicProperty(LIGHT_KEY);
  const form = new ModalFormData()
    .title('光源方塊')
    .slider('亮度', 0, 15, { defaultValue: typeof last === 'number' ? last : 15, valueStep: 1 })
    .textField('數量', '例如 64', { defaultValue: '64' })
    .submitButton('拿取');
  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return back(player);
  const level = Number(response.formValues[0]);
  const amount = parseIntInRange(response.formValues[1], 1, 64 * 36) ?? 64;
  player.setDynamicProperty(LIGHT_KEY, level);
  giveItem(player, lightBlockId(level), amount, `光源方塊（亮度 ${level}）`);
}

/**
 * @param {Player} player
 * @param {import('./catalog.js').CatalogCategory} category
 * @param {Back} back
 */
async function openCategory(player, category, back) {
  const form = new ActionFormData().title(category.label).body('按一下就放進背包。');
  for (const item of category.items) form.button(`${item.label} × ${item.amount}\n§8${item.id}`);
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const item = category.items[response.selection];
  if (item) giveItem(player, item.id, item.amount, item.label);
  else await back(player);
}

/**
 * @param {Player} player
 * @param {Back} [onBack]
 */
export async function openItemsMenu(player, onBack) {
  const self = () => openItemsMenu(player, onBack);
  const form = new ActionFormData().title('常用物品').body('創造模式物品欄沒有、平常要用指令才拿得到的東西。');
  for (const category of CATEGORIES) form.button(category.label);
  form.button('光源方塊（選亮度）');
  form.button('自訂清單');
  form.button('輸入物品 ID…');
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const i = response.selection;
  const n = CATEGORIES.length;
  if (i < n) await openCategory(player, CATEGORIES[i], self);
  else if (i === n) await openLightBlock(player, self);
  else if (i === n + 1) await openCustomList(player, self);
  else if (i === n + 2) await openCustomInput(player, self);
  else if (onBack) await onBack(player);
}
