// 各功能共用的介面工具：提示訊息、顯示表單。

import { system } from '@minecraft/server';
import { ActionFormData, FormCancelationReason } from '@minecraft/server-ui';

/** @typedef {import('@minecraft/server').Player} Player */

/** 正在顯示表單的玩家 @type {Set<string>} */
const formOpen = new Set();

/**
 * 在快捷欄上方顯示一行提示。
 * @param {Player} player
 * @param {string} text
 */
export function notify(player, text) {
  player.onScreenDisplay.setActionBar(text);
}

/** @param {number} ticks */
export function waitTicks(ticks) {
  return new Promise((resolve) => system.runTimeout(() => resolve(undefined), ticks));
}

/** @param {Player} player */
export function isFormOpen(player) {
  return formOpen.has(player.id);
}

/** @param {string} playerId */
export function forgetPlayer(playerId) {
  formOpen.delete(playerId);
}

/**
 * 顯示表單。玩家正在打字（例如剛輸入指令）時表單會被擋下，稍等一下再試。
 * @template {{ show(player: Player): Promise<import('@minecraft/server-ui').FormResponse> }} F
 * @param {Player} player
 * @param {F} form
 * @returns {Promise<Awaited<ReturnType<F['show']>> | undefined>}
 */
export async function showForm(player, form) {
  formOpen.add(player.id);
  try {
    for (let attempt = 0; attempt < 30; attempt++) {
      const response = /** @type {Awaited<ReturnType<F['show']>>} */ (await form.show(player));
      if (response.cancelationReason !== FormCancelationReason.UserBusy) return response;
      await waitTicks(10);
      if (!player.isValid) return undefined;
    }
    return undefined;
  } finally {
    formOpen.delete(player.id);
  }
}

/**
 * 跳出警告，玩家按「知道了」或 X 才繼續。
 * @param {Player} player
 * @param {string} title
 * @param {string} body
 */
export async function showWarning(player, title, body) {
  await showForm(player, new ActionFormData().title(`§c${title}`).body(body).button('知道了'));
}

/**
 * 取得玩家的背包。
 * @param {Player} player
 */
export function inventoryOf(player) {
  const container = player.getComponent('minecraft:inventory')?.container;
  if (!container) throw new Error('讀不到玩家的背包');
  return container;
}
