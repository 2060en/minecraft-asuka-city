// 快速建造：開啟後，玩家每放一顆方塊，就朝玩家面向的方向自動補上後面幾格，可以設定間隔。

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

/** 一次最多補幾顆 */
const MAX_COUNT = 1000;
/** 間隔最多幾格 */
const MAX_GAP = 256;
/** 每位玩家最多保留幾次復原紀錄（只存在記憶體，重新進入世界後會清空） */
const MAX_UNDO = 20;
/** 設定存在玩家身上的 dynamic property 名稱 */
const SETTINGS_KEY = 'qb:settings';

const MODE_OPTIONS = [
  { id: DirectionMode.Horizontal, label: '水平八方位（看正上、正下時改成垂直）', short: '水平' },
  { id: DirectionMode.Snap3D, label: '立體 26 方位（含 45° 斜線）', short: '立體' },
  { id: DirectionMode.Free, label: '自由角度（完全照視線）', short: '自由' },
];
const REPLACE_OPTIONS = [
  { id: 'air', label: '只放在空氣', short: '只放空氣' },
  { id: 'airLiquid', label: '空氣和液體（水、岩漿）', short: '空氣和液體' },
  { id: 'all', label: '全部覆蓋（箱子等容器除外）', short: '全部覆蓋' },
];
const OBSTACLE_OPTIONS = [
  { id: 'stop', label: '停下來', short: '停下' },
  { id: 'skip', label: '跳過，繼續往後放', short: '跳過' },
];

/**
 * @typedef {object} Settings
 * @property {number} count 自動補上幾顆（不含自己放的第一顆）
 * @property {number} gap 每顆之間空幾格
 * @property {string} mode 方向模式
 * @property {string} replace 可以覆蓋哪些方塊
 * @property {string} obstacle 遇到放不下的位置時
 */

/** @type {Settings} */
const DEFAULT_SETTINGS = {
  count: 20,
  gap: 0,
  mode: DirectionMode.Horizontal,
  replace: 'airLiquid',
  obstacle: 'stop',
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
    count: parseIntInRange(raw.count, 1, MAX_COUNT) ?? DEFAULT_SETTINGS.count,
    gap: parseIntInRange(raw.gap, 0, MAX_GAP) ?? DEFAULT_SETTINGS.gap,
    mode: pickOption(String(raw.mode), MODE_OPTIONS, DEFAULT_SETTINGS.mode),
    replace: pickOption(String(raw.replace), REPLACE_OPTIONS, DEFAULT_SETTINGS.replace),
    obstacle: pickOption(String(raw.obstacle), OBSTACLE_OPTIONS, DEFAULT_SETTINGS.obstacle),
  };
}

/**
 * @param {Player} player
 * @returns {Settings}
 */
export function loadSettings(player) {
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
export function settingsSummary(s) {
  return `數量 ${s.count}、間隔 ${s.gap}、${shortLabel(s.mode, MODE_OPTIONS)}`;
}

// ---------------------------------------------------------------------------
// 開關與提示
// ---------------------------------------------------------------------------

/** @param {Player} player */
export function isEnabled(player) {
  return enabledPlayers.get(player.id) === true;
}

/**
 * @param {Player} player
 * @param {boolean} on
 */
export function setEnabled(player, on) {
  enabledPlayers.set(player.id, on);
  if (on) notify(player, `§a快速建造：開啟§r（${settingsSummary(loadSettings(player))}）`);
  else notify(player, '§7快速建造：關閉');
  player.playSound('random.click', { pitch: on ? 1.2 : 0.8 });
}

// ---------------------------------------------------------------------------
// 放方塊
// ---------------------------------------------------------------------------

const WATER_TYPES = new Set(['minecraft:water', 'minecraft:flowing_water']);

/**
 * 這一格可不可以放。
 * @param {Block} block
 * @param {string} replace
 */
function canReplace(block, replace) {
  if (block.isAir) return true;
  if (replace === 'airLiquid') return block.isLiquid;
  if (replace === 'all') {
    if (block.typeId === 'minecraft:bedrock') return false;
    // 容器裡的東西沒辦法復原，所以永遠不覆蓋
    try {
      if (block.getComponent('minecraft:inventory')) return false;
    } catch {
      // 讀不到元件時當作不是容器
    }
    return true;
  }
  return false;
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
 * 主功能：從玩家剛放的方塊開始，往面向的方向補上方塊。
 * @param {Player} player
 * @param {Block} block 玩家剛放的方塊
 * @param {Dimension} dimension
 */
function quickBuild(player, block, dimension) {
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

  const positions = linePositions(origin, step, settings.count, settings.gap);
  const range = dimension.heightRange;
  /** @type {BlockRecord[]} */
  const records = [];
  let placed = 0;
  let skipped = 0;
  let stopReason = '';

  for (const pos of positions) {
    const topY = topPermutation ? pos.y + 1 : pos.y;
    if (pos.y < range.min || topY >= range.max) {
      stopReason = '超出世界高度';
      break;
    }

    /** @type {Block | undefined} */
    let target;
    try {
      target = dimension.getBlock(pos);
    } catch {
      target = undefined;
    }
    if (!target) {
      stopReason = '前方的區塊還沒載入';
      break;
    }
    const top = topPermutation ? target.above() : undefined;
    if (topPermutation && !top) {
      stopReason = '前方的區塊還沒載入';
      break;
    }

    // 已經是同一種方塊（例如和上一條線重疊）就直接跳過，不算擋住
    if (samePermutation(target.permutation, basePermutation)) continue;

    const free = canReplace(target, settings.replace) && (!top || canReplace(top, settings.replace));
    if (!free) {
      if (settings.obstacle === 'stop') {
        stopReason = '被方塊擋住';
        break;
      }
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
 * 復原最近一次快速建造（不包含玩家自己放的第一顆）。
 * @param {Player} player
 */
export function undoLast(player) {
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
    let block;
    try {
      block = dimension.getBlock(rec);
    } catch {
      block = undefined;
    }
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
  message += `§r，還可以復原 ${stack?.length ?? 0} 次`;
  notify(player, message);
}

// ---------------------------------------------------------------------------
// 快速建造選單
// ---------------------------------------------------------------------------

/**
 * @param {Player} player
 * @param {(player: Player) => Promise<void>} [onBack] 按「返回」時要回到的選單
 */
export async function openQuickBuildMenu(player, onBack) {
  const settings = loadSettings(player);
  const on = isEnabled(player);
  const undoCount = undoStacks.get(player.id)?.length ?? 0;

  const body = [
    `狀態：${on ? '§a開啟' : '§7關閉'}§r`,
    `數量：${settings.count} 顆`,
    `間隔：${settings.gap === 0 ? '0（連續）' : `${settings.gap} 格`}`,
    `方向：${shortLabel(settings.mode, MODE_OPTIONS)}`,
    `覆蓋：${shortLabel(settings.replace, REPLACE_OPTIONS)}`,
    `遇到擋住：${shortLabel(settings.obstacle, OBSTACLE_OPTIONS)}`,
    '',
    '§7小技巧：拿木棍蹲下右鍵可以直接開關。',
  ].join('\n');

  const form = new ActionFormData()
    .title('快速建造')
    .body(body)
    .button(on ? '§c關閉快速建造' : '§2開啟快速建造')
    .button('調整設定')
    .button(undoCount > 0 ? `復原上一次（還有 ${undoCount} 次）` : '§8復原上一次（沒有紀錄）')
    .button('使用說明')
    .button('返回');

  const response = await showForm(player, form);
  if (!response || response.canceled) return;
  switch (response.selection) {
    case 0:
      setEnabled(player, !on);
      break;
    case 1:
      await openSettings(player);
      break;
    case 2:
      undoLast(player);
      break;
    case 3:
      await openHelp(player, onBack);
      break;
    case 4:
      if (onBack) await onBack(player);
      break;
  }
}

/**
 * @param {{ id: string }[]} options
 * @param {string} id
 */
function indexOfOption(options, id) {
  return Math.max(0, options.findIndex((o) => o.id === id));
}

/** @param {Player} player */
async function openSettings(player) {
  const s = loadSettings(player);
  const form = new ModalFormData()
    .title('快速建造設定')
    .toggle('開啟快速建造', { defaultValue: isEnabled(player) })
    .textField(`數量：自動補上幾顆（1～${MAX_COUNT}，不含自己放的第一顆）`, '例如 100', {
      defaultValue: String(s.count),
    })
    .textField(`間隔：每顆之間空幾格（0～${MAX_GAP}，0 是連續）`, '例如 3', {
      defaultValue: String(s.gap),
    })
    .dropdown(
      '方向',
      MODE_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(MODE_OPTIONS, s.mode) },
    )
    .dropdown(
      '可以覆蓋哪些方塊',
      REPLACE_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(REPLACE_OPTIONS, s.replace) },
    )
    .dropdown(
      '遇到放不下的位置',
      OBSTACLE_OPTIONS.map((o) => o.label),
      { defaultValueIndex: indexOfOption(OBSTACLE_OPTIONS, s.obstacle) },
    )
    .submitButton('儲存');

  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return;
  const [on, countText, gapText, modeIndex, replaceIndex, obstacleIndex] = response.formValues;

  const count = parseIntInRange(countText, 1, MAX_COUNT);
  const gap = parseIntInRange(gapText, 0, MAX_GAP);
  const next = sanitizeSettings({
    count: count ?? s.count,
    gap: gap ?? s.gap,
    mode: MODE_OPTIONS[Number(modeIndex)]?.id ?? s.mode,
    replace: REPLACE_OPTIONS[Number(replaceIndex)]?.id ?? s.replace,
    obstacle: OBSTACLE_OPTIONS[Number(obstacleIndex)]?.id ?? s.obstacle,
  });
  saveSettings(player, next);
  enabledPlayers.set(player.id, on === true);

  const warnings = [];
  if (count === undefined) warnings.push('數量不是數字，沿用原本的設定');
  if (gap === undefined) warnings.push('間隔不是數字，沿用原本的設定');
  if (warnings.length > 0) player.sendMessage(`§e快速建造：${warnings.join('；')}`);
  notify(player, `${on ? '§a快速建造：開啟' : '§7快速建造：關閉'}§r（${settingsSummary(next)}）`);
}

/**
 * @param {Player} player
 * @param {(player: Player) => Promise<void>} [onBack]
 */
async function openHelp(player, onBack) {
  const body = [
    '§l基本用法§r',
    '1. 拿木棍右鍵開選單 → 快速建造 → 開啟。也可以拿木棍蹲下右鍵直接開關。',
    '2. 拿方塊，面向想要延伸的方向，放下第一顆。',
    '3. 後面的方塊會自動補上，方塊的朝向和第一顆一樣（樓梯、原木、半磚都適用）。',
    '',
    '§l間隔§r',
    '間隔 0 是連續一整排；間隔 3 是「放一顆、空三格、再放一顆」，適合路燈、柱子、行道樹。',
    '',
    '§l方向§r',
    '水平：八個方位（東西南北和四個斜角），抬頭或低頭超過 75° 時改成垂直。',
    '立體：再加上 45° 往上或往下的斜線，可以蓋樓梯、斜坡。',
    '自由：完全照視線方向，可以做出任意斜率，但比較難瞄準。',
    '',
    '§l往上長柱子§r',
    '線如果一開始就要鑽進第一顆方塊貼著的那顆方塊，會自動反過來長：',
    '看著正下方的地面放 → 往上長柱子；看著天花板放 → 往下垂；看著牆面放 → 從牆面往外長。',
    '',
    '§l復原§r',
    `選單裡可以復原最近 ${MAX_UNDO} 次快速建造，只會收回自動補上的方塊，不包含自己放的第一顆。`,
    '復原紀錄只存在記憶體，離開世界後就會清空。',
    '',
    '§l指令（備用）§r',
    '/asuka:menu 開選單；/asuka:undo 復原上一次快速建造。',
  ].join('\n');
  const response = await showForm(player, new ActionFormData().title('快速建造說明').body(body).button('返回選單'));
  if (response && !response.canceled) await openQuickBuildMenu(player, onBack);
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
    quickBuild(player, block, dimension);
  } catch (error) {
    console.warn(`[快速建造] ${error}`);
    notify(player, `§c快速建造發生錯誤：${error}`);
  }
}

/** @param {string} playerId */
export function forgetQuickBuildPlayer(playerId) {
  enabledPlayers.delete(playerId);
  undoStacks.delete(playerId);
  lastInteract.delete(playerId);
}
