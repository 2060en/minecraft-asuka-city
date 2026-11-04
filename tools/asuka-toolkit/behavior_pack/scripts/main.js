// Asuka 工具包
//
// 只使用穩定版 Script API（不需要開啟實驗性功能），只放原版方塊與原版物品，拔掉行為包不影響世界。
//
// 功能：
//   快速建造   放一顆方塊，朝面向的方向自動補上後面幾格（quickbuild.js）
//   常用物品   要用指令才拿得到的東西做成選單（items.js）
//   物品收藏   把旗幟、盾牌等物品存起來，隨時拿一份（favorites.js）
//   時間與天氣 一鍵切換白天／晚上、天氣（environment.js）
//
// 操作：
//   拿木棍右鍵                → 開主選單
//   拿木棍蹲下右鍵            → 直接開關快速建造
//   /asuka:menu、/asuka:undo → 用指令開選單、復原快速建造（備用）

import { world, system, CommandPermissionLevel, CustomCommandStatus } from '@minecraft/server';
import { ActionFormData } from '@minecraft/server-ui';
import {
  openQuickBuildMenu,
  setEnabled,
  isEnabled,
  undoLast,
  loadSettings,
  settingsSummary,
  recordInteract,
  onPlayerPlaceBlock,
  forgetQuickBuildPlayer,
} from './quickbuild.js';
import { openItemsMenu } from './items.js';
import { openFavoritesMenu } from './favorites.js';
import { openEnvironmentMenu } from './environment.js';
import { notify, showForm, isFormOpen, forgetPlayer } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */

/** 開選單用的物品 */
const MENU_ITEM = 'minecraft:stick';

/** 防止一次右鍵觸發兩次選單 @type {Map<string, number>} */
const lastMenuTick = new Map();

/**
 * 執行選單動作，出錯時提示玩家而不是讓錯誤消失。
 * @param {Player} player
 * @param {(player: Player) => Promise<void> | void} action
 */
async function safely(player, action) {
  try {
    await action(player);
  } catch (error) {
    console.warn(`[Asuka 工具包] ${error}`);
    if (player.isValid) notify(player, `§c發生錯誤：${error}`);
  }
}

/** @param {Player} player */
async function openMainMenu(player) {
  if (isFormOpen(player)) return;
  const on = isEnabled(player);
  const form = new ActionFormData()
    .title('Asuka 工具包')
    .body(`快速建造：${on ? '§a開啟' : '§7關閉'}§r（${settingsSummary(loadSettings(player))}）`)
    .button('快速建造')
    .button('常用物品')
    .button('物品收藏（旗幟、盾牌…）')
    .button('時間與天氣');
  const response = await showForm(player, form);
  if (!response || response.canceled) return;
  switch (response.selection) {
    case 0:
      await openQuickBuildMenu(player, openMainMenu);
      break;
    case 1:
      await openItemsMenu(player, openMainMenu);
      break;
    case 2:
      await openFavoritesMenu(player, openMainMenu);
      break;
    case 3:
      await openEnvironmentMenu(player, openMainMenu);
      break;
  }
}

/**
 * 拿木棍右鍵：蹲下時直接開關快速建造，否則開主選單。
 * @param {Player} player
 */
function onMenuItemUse(player) {
  const now = system.currentTick;
  const last = lastMenuTick.get(player.id);
  if (last !== undefined && now - last < 10) return;
  lastMenuTick.set(player.id, now);
  if (player.isSneaking) setEnabled(player, !isEnabled(player));
  else void safely(player, openMainMenu);
}

// ---------------------------------------------------------------------------
// 事件
// ---------------------------------------------------------------------------

world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
  const { player, block } = event;
  recordInteract(player, block, event.blockFace);
  // 拿木棍點方塊時不要觸發方塊本身的功能（例如開門、開箱子），改成開選單
  if (event.itemStack?.typeId === MENU_ITEM) {
    event.cancel = true;
    if (event.isFirstEvent) system.run(() => onMenuItemUse(player));
  }
});

world.afterEvents.itemUse.subscribe((event) => {
  if (event.itemStack?.typeId === MENU_ITEM) onMenuItemUse(event.source);
});

world.afterEvents.playerPlaceBlock.subscribe((event) => {
  onPlayerPlaceBlock(event.player, event.block, event.dimension);
});

world.afterEvents.playerLeave.subscribe(({ playerId }) => {
  forgetQuickBuildPlayer(playerId);
  forgetPlayer(playerId);
  lastMenuTick.delete(playerId);
});

// 備用指令：/asuka:menu、/asuka:undo
system.beforeEvents.startup.subscribe(({ customCommandRegistry }) => {
  /**
   * @param {import('@minecraft/server').CustomCommandOrigin} origin
   * @param {(player: Player) => Promise<void> | void} action
   * @returns {import('@minecraft/server').CustomCommandResult}
   */
  const runForPlayer = (origin, action) => {
    const entity = origin.sourceEntity;
    if (!entity || entity.typeId !== 'minecraft:player') {
      return { status: CustomCommandStatus.Failure, message: '只有玩家可以使用這個指令' };
    }
    const player = /** @type {Player} */ (entity);
    system.run(() => void safely(player, action));
    return { status: CustomCommandStatus.Success };
  };

  customCommandRegistry.registerCommand(
    {
      name: 'asuka:menu',
      description: '開啟 Asuka 工具包選單',
      permissionLevel: CommandPermissionLevel.Any,
      cheatsRequired: false,
    },
    (origin) => runForPlayer(origin, openMainMenu),
  );
  customCommandRegistry.registerCommand(
    {
      name: 'asuka:undo',
      description: '復原上一次快速建造',
      permissionLevel: CommandPermissionLevel.Any,
      cheatsRequired: false,
    },
    (origin) => runForPlayer(origin, undoLast),
  );
});
