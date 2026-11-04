// 快速建造（木棍）：開啟後，玩家每放一顆方塊，就朝面向的方向自動補上後面幾格；
// 每打掉一顆，就朝面向的方向打掉後面幾格。範圍含第一顆，間隔是中間空幾格。

import { world, system } from '@minecraft/server';
import { ActionFormData, ModalFormData } from '@minecraft/server-ui';
import {
  DirectionMode,
  stepFromView,
  linePositions,
  faceNormal,
  shouldFlip,
  negate,
  pointAt,
  parseIntInRange,
  describeDirection,
  topPermutationOf,
} from './line.js';
import { notify, showForm } from './ui.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {import('@minecraft/server').BlockPermutation} BlockPermutation */
/** @typedef {import('@minecraft/server').Block} Block */
/** @typedef {import('@minecraft/server').Dimension} Dimension */
/** @typedef {import('./line.js').Vec3} Vec3 */

// ---------------------------------------------------------------------------
// 設定值
// ---------------------------------------------------------------------------

/** 範圍最多幾格 */
const MAX_RANGE = 1000;
/** 間隔最多幾格 */
const MAX_GAP = 256;
/** 每位玩家最多保留幾次復原紀錄（只存在記憶體，重新進入世界後會清空） */
const MAX_UNDO = 20;
/** 設定存在玩家身上的 dynamic property 名稱 */
const SETTINGS_KEY = 'qb:settings2';

const MODE_OPTIONS = [
  { id: DirectionMode.Horizontal, label: '水平八方位（看正上、正下時改成垂直）', short: '水平' },
  { id: DirectionMode.Snap3D, label: '立體 26 方位（含 45° 斜線）', short: '立體' },
  { id: DirectionMode.Free, label: '自由角度（完全照視線）', short: '自由' },
];
const REPLACE_OPTIONS = [
  { id: 'air', label: '只放在空氣', short: '只放空氣' },
  { id: 'airLiquid', label: '空氣和液體（水、岩漿）', short: '空氣和液體' },
  { id: 'all', label: '全部覆蓋（基岩、箱子等容器除外）', short: '全部覆蓋' },
];
const BREAK_OPTIONS = [
  { id: 'all', label: '全部（基岩、箱子等容器除外）', short: '全部' },
  { id: 'same', label: '和第一顆同一種的方塊', short: '同一種' },
];

/**
 * @typedef {object} Settings
 * @property {number} range 範圍：幾格內，含自己放或打的第一顆
 * @property {number} gap 每顆之間空幾格
 * @property {string} mode 方向模式
 * @property {string} replace 放置時可以蓋掉哪些方塊
 * @property {string} breakOnly 破壞時只打哪些方塊
 */

/** @type {Settings} */
const DEFAULT_SETTINGS = {
  range: 20,
  gap: 0,
  mode: DirectionMode.Horizontal,
  replace: 'all',
  breakOnly: 'all',
};

// ---------------------------------------------------------------------------
// 狀態（只存在記憶體）
// ---------------------------------------------------------------------------

/** 每位玩家是否開啟快速建造；每次進入世界都從關閉開始 @type {Map<string, boolean>} */
const enabledPlayers = new Map();
/**
 * @typedef {{ x: number, y: number, z: number, permutation: BlockPermutation, waterlogged: boolean }} BlockRecord
 * @typedef {{ dimensionId: string, records: BlockRecord[] }} UndoEntry
 */
/** @type {Map<string, UndoEntry[]>} */
const undoStacks = new Map();
/** 玩家最近一次右鍵點到的方塊與面，用來判斷第一顆方塊貼在哪 @type {Map<string, { x: number, y: number, z: number, face: string, tick: number }>} */
const lastInteract = new Map();

// ---------------------------------------------------------------------------
// 設定的讀寫
// ---------------------------------------------------------------------------

/**
 * @param {string} id
 * @param {{ id: string }[]} options
 * @param {string} fallback
 */
function pickOption(id, options, fallback) {
  return options.some((o) => o.id === id) ? id : fallback;
}

/**
 * @param {Partial<Settings>} raw
 * @returns {Settings}
 */
function sanitizeSettings(raw) {
  return {
    range: parseIntInRange(raw.range, 1, MAX_RANGE) ?? DEFAULT_SETTINGS.range,
    gap: parseIntInRange(raw.gap, 0, MAX_GAP) ?? DEFAULT_SETTINGS.gap,
    mode: pickOption(String(raw.mode), MODE_OPTIONS, DEFAULT_SETTINGS.mode),
    replace: pickOption(String(raw.replace), REPLACE_OPTIONS, DEFAULT_SETTINGS.replace),
    breakOnly: pickOption(String(raw.breakOnly), BREAK_OPTIONS, DEFAULT_SETTINGS.breakOnly),
  };
}

/**
 * @param {Player} player
 * @returns {Settings}
 */
function loadSettings(player) {
  let parsed = {};
  try {
    const raw = player.getDynamicProperty(SETTINGS_KEY);
    if (typeof raw === 'string') parsed = JSON.parse(raw);
  } catch {
    // 設定壞掉時用預設值
  }
  return sanitizeSettings({ ...DEFAULT_SETTINGS, ...parsed });
}

/**
 * @param {Player} player
 * @param {Settings} settings
 */
function saveSettings(player, settings) {
  player.setDynamicProperty(SETTINGS_KEY, JSON.stringify(settings));
}

/**
 * @param {string} id
 * @param {{ id: string, short: string }[]} options
 */
function shortLabel(id, options) {
  return options.find((o) => o.id === id)?.short ?? id;
}

/** @param {Settings} s */
function settingsSummary(s) {
  return `範圍 ${s.range}、間隔 ${s.gap}、${shortLabel(s.mode, MODE_OPTIONS)}`;
}

// ---------------------------------------------------------------------------
// 開關
// ---------------------------------------------------------------------------

/** @param {Player} player */
function isEnabled(player) {
  return enabledPlayers.get(player.id) === true;
}

/**
 * 蹲下＋木棍右鍵：開關快速建造。
 * @param {Player} player
 */
export function toggleQuickBuild(player) {
  const on = !isEnabled(player);
  enabledPlayers.set(player.id, on);
  if (on) notify(player, `§a快速建造：開啟§r（${settingsSummary(loadSettings(player))}）`);
  else notify(player, '§7快速建造：關閉');
  player.playSound('random.click', { pitch: on ? 1.2 : 0.8 });
}

// ---------------------------------------------------------------------------
// 放方塊與打方塊
// ---------------------------------------------------------------------------

const WATER_TYPES = new Set(['minecraft:water', 'minecraft:flowing_water']);
/** 兩格高的方塊用哪個狀態分上下半：原版與 Asuka tech 的門 */
const UPPER_STATES = ['upper_block_bit', 'asukatech:upper'];

/**
 * 基岩不能動；容器裡的東西沒辦法復原，所以也不動。
 * @param {Block} block
 */
function isProtected(block) {
  if (block.typeId === 'minecraft:bedrock') return true;
  try {
    if (block.getComponent('minecraft:inventory')) return true;
  } catch {
    // 讀不到元件時當作不是容器
  }
  return false;
}

/**
 * 這一格可不可以放。
 * @param {Block} block
 * @param {string} replace
 */
function canReplace(block, replace) {
  if (block.isAir) return true;
  if (replace === 'airLiquid') return block.isLiquid;
  if (replace === 'all') return !isProtected(block);
  return false;
}

/**
 * 這一格可不可以打。空氣和液體不算方塊，床是兩格而且顏色存在方塊實體裡，復原不回來。
 * @param {Block} block
 * @param {BlockPermutation} first 第一顆
 * @param {string} breakOnly
 */
function canBreak(block, first, breakOnly) {
  if (block.isAir || block.isLiquid || isProtected(block)) return false;
  if (block.permutation.getState('head_piece_bit') !== undefined) return false;
  return breakOnly !== 'same' || block.typeId === first.type.id;
}

/**
 * 兩格高的方塊的另一半。
 * @param {Block} block
 * @returns {Block | undefined}
 */
function otherHalf(block) {
  for (const state of UPPER_STATES) {
    const upper = block.permutation.getState(state);
    if (upper === undefined) continue;
    const other = upper ? block.below() : block.above();
    return other?.typeId === block.typeId ? other : undefined;
  }
  return undefined;
}

/**
 * @param {BlockPermutation} a
 * @param {BlockPermutation} b
 */
function samePermutation(a, b) {
  return a.type.id === b.type.id && JSON.stringify(a.getAllStates()) === JSON.stringify(b.getAllStates());
}

/**
 * @param {Block} block
 * @returns {BlockRecord}
 */
function recordBlock(block) {
  return { x: block.x, y: block.y, z: block.z, permutation: block.permutation, waterlogged: block.isWaterlogged };
}

/**
 * @param {Block} block
 * @param {BlockPermutation} permutation
 * @param {boolean} waterlogged 第一顆方塊是否含水
 */
function placeBlock(block, permutation, waterlogged) {
  const wasWater = WATER_TYPES.has(block.typeId);
  block.setPermutation(permutation);
  // 第一顆是在水裡放的含水方塊（例如水中的柵欄、半磚）時，後面的也保持含水
  if (waterlogged && wasWater) {
    try {
      block.setWaterlogged(true);
    } catch {
      // 這種方塊不能含水
    }
  }
}

/**
 * 找出第一顆方塊貼著哪一顆方塊。
 * 放方塊時遊戲會先觸發「右鍵點方塊」事件，記下點到的方塊和面，
 * 點到的方塊加上面的方向等於新方塊的位置，就代表新方塊是貼著它放的。
 * @param {Player} player
 * @param {Vec3} origin
 * @returns {Vec3 | undefined}
 */
function findSupport(player, origin) {
  const hit = lastInteract.get(player.id);
  if (!hit || system.currentTick - hit.tick > 2) return undefined;
  const normal = faceNormal(hit.face);
  if (!normal) return undefined;
  const support = { x: hit.x, y: hit.y, z: hit.z };
  const expected = { x: support.x + normal.x, y: support.y + normal.y, z: support.z + normal.z };
  return expected.x === origin.x && expected.y === origin.y && expected.z === origin.z ? support : undefined;
}

/**
 * @param {Player} player
 * @param {UndoEntry} entry
 */
function pushUndo(player, entry) {
  const stack = undoStacks.get(player.id) ?? [];
  stack.push(entry);
  while (stack.length > MAX_UNDO) stack.shift();
  undoStacks.set(player.id, stack);
}

/**
 * @param {Dimension} dimension
 * @param {Vec3} pos
 * @returns {Block | undefined}
 */
function getBlockAt(dimension, pos) {
  try {
    return dimension.getBlock(pos);
  } catch {
    return undefined;
  }
}

/**
 * 從玩家剛放的方塊開始，往面向的方向補上方塊。
 * @param {Player} player
 * @param {Block} block 玩家剛放的方塊
 * @param {Dimension} dimension
 */
function quickPlace(player, block, dimension) {
  const settings = loadSettings(player);
  const origin = { x: block.x, y: block.y, z: block.z };
  const basePermutation = block.permutation;
  const baseWaterlogged = block.isWaterlogged;

  if (basePermutation.getState('head_piece_bit') !== undefined) {
    notify(player, '§e快速建造：不支援床');
    return;
  }

  // 兩格高的方塊（門、高草、向日葵等）：上半部一起複製
  const above = block.above();
  const topPermutation = topPermutationOf(basePermutation, above?.permutation);
  const topWaterlogged = Boolean(topPermutation && above?.isWaterlogged);

  // 決定方向
  let step = stepFromView(player.getViewDirection(), settings.mode);
  const support = findSupport(player, origin);
  if (support) {
    if (shouldFlip(origin, step, support)) step = negate(step);
  } else if (step.x === 0 && step.z === 0) {
    // 不知道貼著哪顆方塊時的備案：垂直方向第一格就放不下，就反過來
    const first = dimension.getBlock(pointAt(origin, step, 1));
    if (first && !canReplace(first, settings.replace)) step = negate(step);
  }

  const positions = linePositions(origin, step, settings.range, settings.gap);
  const heights = dimension.heightRange;
  /** @type {BlockRecord[]} */
  const records = [];
  let placed = 0;
  let skipped = 0;
  let stopReason = '';

  for (const pos of positions) {
    const topY = topPermutation ? pos.y + 1 : pos.y;
    if (pos.y < heights.min || topY >= heights.max) {
      stopReason = '超出世界高度';
      break;
    }
    const target = getBlockAt(dimension, pos);
    const top = topPermutation ? target?.above() : undefined;
    if (!target || (topPermutation && !top)) {
      stopReason = '前方的區塊還沒載入';
      break;
    }

    // 已經是同一種方塊（例如和上一條線重疊）就直接跳過
    if (samePermutation(target.permutation, basePermutation)) continue;

    if (!canReplace(target, settings.replace) || (top && !canReplace(top, settings.replace))) {
      skipped++;
      continue;
    }

    records.push(recordBlock(target));
    placeBlock(target, basePermutation, baseWaterlogged);
    if (top && topPermutation) {
      records.push(recordBlock(top));
      placeBlock(top, topPermutation, topWaterlogged);
    }
    placed++;
  }

  if (records.length > 0) pushUndo(player, { dimensionId: dimension.id, records });

  const direction = describeDirection(step, settings.mode);
  if (placed === 0) {
    notify(player, `§e快速建造：往${direction}一顆都沒放${stopReason ? `（${stopReason}）` : ''}`);
    return;
  }
  let message = `§a快速建造§r：往${direction}放了 ${placed} 顆`;
  if (skipped > 0) message += `，跳過 ${skipped} 格`;
  if (stopReason) message += `§e（${stopReason}，提早停下）`;
  notify(player, message);
}

/**
 * 從玩家剛打掉的方塊開始，往面向的方向打掉後面的方塊。不會掉物品（作者要求，2026-11-05）。
 * @param {Player} player
 * @param {Block} block 玩家剛打掉的那一格（現在已經空了）
 * @param {BlockPermutation} broken 打掉之前的樣子
 * @param {Dimension} dimension
 */
function quickBreak(player, block, broken, dimension) {
  const settings = loadSettings(player);
  const origin = { x: block.x, y: block.y, z: block.z };
  const step = stepFromView(player.getViewDirection(), settings.mode);
  const heights = dimension.heightRange;

  /** @type {BlockRecord[]} */
  const records = [];
  // 第一顆也記下來，復原時才不會留一個洞；兩格高的方塊另一半已經不見了，復原不完整，所以不記
  if (!UPPER_STATES.some((state) => broken.getState(state) !== undefined)) {
    records.push({ ...origin, permutation: broken, waterlogged: false });
  }

  let cleared = 0;
  let stopReason = '';
  for (const pos of linePositions(origin, step, settings.range, settings.gap)) {
    if (pos.y < heights.min || pos.y >= heights.max) {
      stopReason = '超出世界高度';
      break;
    }
    const target = getBlockAt(dimension, pos);
    if (!target) {
      stopReason = '前方的區塊還沒載入';
      break;
    }
    if (!canBreak(target, broken, settings.breakOnly)) continue;

    // 兩格高的方塊兩半一起拿掉，才不會掉落或留下半扇門
    const other = otherHalf(target);
    if (other) {
      records.push(recordBlock(other));
      other.setType('minecraft:air');
    }
    records.push(recordBlock(target));
    target.setType('minecraft:air');
    cleared++;
  }

  if (records.length > 0) pushUndo(player, { dimensionId: dimension.id, records });

  const direction = describeDirection(step, settings.mode);
  let message = `§a快速破壞§r：往${direction}打掉 ${cleared} 顆`;
  if (stopReason) message += `§e（${stopReason}，提早停下）`;
  notify(player, message);
}

/**
 * 復原最近一次快速建造或快速破壞。
 * @param {Player} player
 */
function undoLast(player) {
  const stack = undoStacks.get(player.id);
  const entry = stack?.pop();
  if (!entry) {
    notify(player, '§7快速建造：沒有可以復原的紀錄');
    return;
  }
  const dimension = world.getDimension(entry.dimensionId);
  let restored = 0;
  let missing = 0;
  for (const rec of [...entry.records].reverse()) {
    const block = getBlockAt(dimension, rec);
    if (!block) {
      missing++;
      continue;
    }
    block.setPermutation(rec.permutation);
    if (rec.waterlogged) {
      try {
        block.setWaterlogged(true);
      } catch {
        // 不能含水就算了
      }
    }
    restored++;
  }
  let message = `§a快速建造：已復原 ${restored} 格`;
  if (missing > 0) message += `§e（${missing} 格所在的區塊沒有載入，無法復原）`;
  notify(player, message);
}

// ---------------------------------------------------------------------------
// 介面
// ---------------------------------------------------------------------------

/**
 * 木棍右鍵的頁面。按「復原」不關頁面，要復原好幾次不用一直開
 * （遊戲的表單按了就關，所以是馬上重開同一頁）。
 * @param {Player} player
 */
export async function openQuickBuildPanel(player) {
  for (;;) {
    const s = loadSettings(player);
    const undoCount = undoStacks.get(player.id)?.length ?? 0;
    const form = new ActionFormData()
      .title('快速建造')
      .body(
        [
          `狀態：${isEnabled(player) ? '§a開啟' : '§7關閉'}§r（蹲下＋木棍右鍵開關）`,
          settingsSummary(s),
          `可以蓋掉：${shortLabel(s.replace, REPLACE_OPTIONS)}；破壞時只打：${shortLabel(s.breakOnly, BREAK_OPTIONS)}`,
        ].join('\n'),
      )
      .button(undoCount > 0 ? `復原上一次（還有 ${undoCount} 次）` : '§8復原上一次（沒有紀錄）')
      .button('調整設定');

    const response = await showForm(player, form);
    if (!response || response.canceled) return;
    if (response.selection === 0) undoLast(player);
    else if (await openSettings(player)) return;
  }
}

/**
 * @param {{ id: string }[]} options
 * @param {string} id
 */
function indexOfOption(options, id) {
  return Math.max(0, options.findIndex((o) => o.id === id));
}

/**
 * @param {Player} player
 * @returns {Promise<boolean>} 按了「套用」就是 true；按 X 回上一頁就是 false
 */
async function openSettings(player) {
  const s = loadSettings(player);
  const form = new ModalFormData()
    .title('快速建造設定')
    .toggle('開啟快速建造', { defaultValue: isEnabled(player) })
    .textField(`範圍：幾格內，含親手放或打的第一顆（1～${MAX_RANGE}）`, '例如 20', {
      defaultValue: String(s.range),
    })
    .textField(`間隔：中間空幾格（0～${MAX_GAP}，0 是連續）`, '例如 2', {
      defaultValue: String(s.gap),
    })
    .dropdown(
      '方向',
      MODE_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(MODE_OPTIONS, s.mode) },
    )
    .dropdown(
      '可以蓋掉',
      REPLACE_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(REPLACE_OPTIONS, s.replace) },
    )
    .dropdown(
      '破壞時只打',
      BREAK_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(BREAK_OPTIONS, s.breakOnly) },
    )
    .submitButton('套用');

  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return false;
  const [on, rangeText, gapText, modeIndex, replaceIndex, breakIndex] = response.formValues;

  const range = parseIntInRange(rangeText, 1, MAX_RANGE);
  const gap = parseIntInRange(gapText, 0, MAX_GAP);
  const next = sanitizeSettings({
    range: range ?? s.range,
    gap: gap ?? s.gap,
    mode: MODE_OPTIONS[Number(modeIndex)]?.id ?? s.mode,
    replace: REPLACE_OPTIONS[Number(replaceIndex)]?.id ?? s.replace,
    breakOnly: BREAK_OPTIONS[Number(breakIndex)]?.id ?? s.breakOnly,
  });
  saveSettings(player, next);
  enabledPlayers.set(player.id, on === true);

  const warnings = [];
  if (range === undefined) warnings.push('範圍不是數字，沿用原本的設定');
  if (gap === undefined) warnings.push('間隔不是數字，沿用原本的設定');
  if (warnings.length > 0) player.sendMessage(`§e快速建造：${warnings.join('；')}`);
  notify(player, `${on ? '§a快速建造：開啟' : '§7快速建造：關閉'}§r（${settingsSummary(next)}）`);
  return true;
}

// ---------------------------------------------------------------------------
// 給 main.js 用的事件處理
// ---------------------------------------------------------------------------

/**
 * 玩家右鍵點到方塊時記下點到的方塊和面（放方塊前遊戲會先觸發這個事件）。
 * @param {Player} player
 * @param {Block} block
 * @param {string} face
 */
export function recordInteract(player, block, face) {
  lastInteract.set(player.id, { x: block.x, y: block.y, z: block.z, face, tick: system.currentTick });
}

/**
 * 玩家放下方塊之後呼叫。
 * @param {Player} player
 * @param {Block} block
 * @param {Dimension} dimension
 */
export function onPlayerPlaceBlock(player, block, dimension) {
  if (!isEnabled(player)) return;
  try {
    quickPlace(player, block, dimension);
  } catch (error) {
    console.warn(`[快速建造] ${error}`);
    notify(player, `§c快速建造發生錯誤：${error}`);
  }
}

/**
 * 玩家打掉方塊之後呼叫。
 * @param {Player} player
 * @param {Block} block
 * @param {BlockPermutation} broken
 * @param {Dimension} dimension
 */
export function onPlayerBreakBlock(player, block, broken, dimension) {
  if (!isEnabled(player)) return;
  try {
    quickBreak(player, block, broken, dimension);
  } catch (error) {
    console.warn(`[快速破壞] ${error}`);
    notify(player, `§c快速破壞發生錯誤：${error}`);
  }
}

/** @param {string} playerId */
export function forgetQuickBuildPlayer(playerId) {
  enabledPlayers.delete(playerId);
  undoStacks.delete(playerId);
  lastInteract.delete(playerId);
}
