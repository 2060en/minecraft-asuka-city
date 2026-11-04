// Asuka 工具包
//
// 只使用穩定版 Script API（不需要開啟實驗性功能），只放原版方塊與原版物品，拔掉行為包不影響世界。
//
// 每樣工具一個功能，全部用手上拿的東西操作（作者定的，2026-11-05）：
//   木棍     右鍵開快速建造（quickbuild.js），蹲下右鍵開關
//   烈焰棒   揮一下或右鍵開收藏清單，蹲下右鍵收藏（favorites.js）
//   旋風棒   揮一下或右鍵開特殊物品（special.js）

import { world, system } from '@minecraft/server';
import { toggleQuickBuild, openQuickBuildPanel, recordInteract, onPlayerPlaceBlock, onPlayerBreakBlock, forgetQuickBuildPlayer } from './quickbuild.js';
import { openFavorites, saveFromBlock, saveRightSlot } from './favorites.js';
import { openSpecialItems } from './special.js';
import { isLeftClickSwing } from './input.js';
import { notify, isFormOpen, forgetPlayer } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {import('@minecraft/server').Block} Block */

const QUICK_BUILD_TOOL = 'minecraft:stick';
const FAVORITES_TOOL = 'minecraft:blaze_rod';
const SPECIAL_TOOL = 'minecraft:breeze_rod';
/** 拿著這些東西左鍵是要開介面，不是要打方塊 */
const SWING_TOOLS = new Set([FAVORITES_TOOL, SPECIAL_TOOL]);

/** 防止一次操作觸發兩次（點方塊時有好幾個事件） @type {Map<string, number>} */
const lastActionTick = new Map();

/** @param {Player} player */
function firstInAWhile(player) {
  const now = system.currentTick;
  const last = lastActionTick.get(player.id);
  if (last !== undefined && now - last < 10) return false;
  lastActionTick.set(player.id, now);
  return true;
}

/**
 * 執行動作，出錯時提示玩家而不是讓錯誤消失。
 * @param {Player} player
 * @param {(player: Player) => Promise<void> | void} action
 */
async function safely(player, action) {
  if (isFormOpen(player)) return;
  try {
    await action(player);
  } catch (error) {
    console.warn(`[Asuka 工具包] ${error}`);
    if (player.isValid) notify(player, `§c發生錯誤：${error}`);
  }
}

/**
 * 右鍵：對方塊時 block 是點到的方塊，對空氣時沒有。
 * @param {Player} player
 * @param {string} tool
 * @param {Block} [block]
 */
function useTool(player, tool, block) {
  if (tool === QUICK_BUILD_TOOL) {
    if (player.isSneaking) toggleQuickBuild(player);
    else void safely(player, openQuickBuildPanel);
  } else if (tool === SPECIAL_TOOL) {
    void safely(player, openSpecialItems);
  } else if (tool === FAVORITES_TOOL) {
    if (!player.isSneaking) void safely(player, openFavorites);
    else if (block) void safely(player, (p) => saveFromBlock(p, block));
    else void safely(player, saveRightSlot);
  }
}

// ---------------------------------------------------------------------------
// 事件
// ---------------------------------------------------------------------------

const RIGHT_CLICK_TOOLS = new Set([QUICK_BUILD_TOOL, FAVORITES_TOOL, SPECIAL_TOOL]);

world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
  const { player, block } = event;
  recordInteract(player, block, event.blockFace);
  // 拿工具點方塊時不要觸發方塊本身的功能（例如開門、開箱子）
  const tool = event.itemStack?.typeId;
  if (tool && RIGHT_CLICK_TOOLS.has(tool)) {
    event.cancel = true;
    if (event.isFirstEvent && firstInAWhile(player)) system.run(() => useTool(player, tool, block));
  }
});

world.afterEvents.itemUse.subscribe((event) => {
  const tool = event.itemStack?.typeId;
  if (tool && RIGHT_CLICK_TOOLS.has(tool) && firstInAWhile(event.source)) useTool(event.source, tool);
});

// 揮一下（左鍵）：開介面
world.afterEvents.playerSwingStart.subscribe(({ player, heldItemStack, swingSource }) => {
  const tool = heldItemStack?.typeId;
  if (!tool || !SWING_TOOLS.has(tool) || !isLeftClickSwing(swingSource) || !firstInAWhile(player)) return;
  void safely(player, tool === FAVORITES_TOOL ? openFavorites : openSpecialItems);
});

// 拿著烈焰棒、旋風棒左鍵點方塊時，只開介面，不要把方塊打掉
world.beforeEvents.playerBreakBlock.subscribe((event) => {
  const tool = event.itemStack?.typeId;
  if (tool && SWING_TOOLS.has(tool)) event.cancel = true;
});

world.afterEvents.playerBreakBlock.subscribe((event) => {
  onPlayerBreakBlock(event.player, event.block, event.brokenBlockPermutation, event.dimension);
});

world.afterEvents.playerPlaceBlock.subscribe((event) => {
  onPlayerPlaceBlock(event.player, event.block, event.dimension);
});

world.afterEvents.playerLeave.subscribe(({ playerId }) => {
  forgetQuickBuildPlayer(playerId);
  forgetPlayer(playerId);
  lastActionTick.delete(playerId);
});
