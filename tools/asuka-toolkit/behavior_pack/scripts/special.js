// 特殊物品（旋風棒）：揮一下開清單，按一下就放進包包；包包滿了跳出警告。

import { ItemStack } from '@minecraft/server';
import { ActionFormData } from '@minecraft/server-ui';
import { SPECIAL_ITEMS } from './catalog.js';
import { notify, showForm, showWarning, inventoryOf } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */

/**
 * 按完不關頁面：連續拿好幾樣不用重開（遊戲的表單按了就關，所以是馬上重開同一頁）。
 * @param {Player} player
 */
export async function openSpecialItems(player) {
  for (;;) {
    const form = new ActionFormData().title('特殊物品').body('按一下就放進包包。');
    for (const item of SPECIAL_ITEMS) form.button(item.amount > 1 ? `${item.label} × ${item.amount}` : item.label);

    const response = await showForm(player, form);
    if (!response || response.canceled || response.selection === undefined) return;

    const item = SPECIAL_ITEMS[response.selection];
    const left = inventoryOf(player).addItem(new ItemStack(item.id, item.amount));
    if (left) await showWarning(player, '包包滿了', `「${item.label}」放不下，先空出一格再拿。`);
    else notify(player, `§a拿到 ${item.label}`);
  }
}
