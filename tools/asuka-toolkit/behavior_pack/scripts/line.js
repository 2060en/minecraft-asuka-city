// 快速建造的純計算部分：方向吸附、線段座標、方向說明。
// 這個檔案不依賴 @minecraft/server，可以直接在電腦上用 Node.js 測試（見 tools/quick-build/test）。

/** @typedef {{ x: number, y: number, z: number }} Vec3 */

/** 方向模式。正上、正下不在這裡，由「上下放」開關決定（作者定的，2026-11-08） */
export const DirectionMode = Object.freeze({
  /** 水平八方位 */
  Horizontal: 'horizontal',
  /** 立體：水平八方位 × 上、平、下，包含 45° 斜線 */
  Snap3D: 'snap3d',
  /** 完全照視線方向，可以做出任意斜率 */
  Free: 'free',
});

/** 立體模式：俯仰角超過這個角度算 45° 斜線 */
export const DIAGONAL_PITCH = 22.5;

/**
 * 四捨五入，.5 一律往遠離 0 的方向進位，讓左右對稱的線長得一樣。
 * @param {number} v
 */
export function roundHalfAway(v) {
  const r = Math.sign(v) * Math.round(Math.abs(v));
  return r === 0 ? 0 : r; // 避免 -0
}

/**
 * 視線的俯仰角（度），正數是抬頭，負數是低頭。
 * @param {Vec3} view
 */
export function pitchOf(view) {
  return (Math.atan2(view.y, Math.hypot(view.x, view.z)) * 180) / Math.PI;
}

/**
 * 把視線的水平分量吸附到最近的八方位。
 * @param {Vec3} view
 * @returns {{ x: number, z: number }} 每個分量是 -1、0 或 1
 */
export function snapHorizontal(view) {
  const octant = Math.round(Math.atan2(view.z, view.x) / (Math.PI / 4));
  const angle = (octant * Math.PI) / 4;
  return { x: roundHalfAway(Math.cos(angle)) || 0, z: roundHalfAway(Math.sin(angle)) || 0 };
}

/**
 * 依照方向模式，把視線方向換算成每一步的位移。
 * 吸附模式回傳整數向量（每個分量 -1、0、1）；自由模式回傳「最大分量為 1」的小數向量，
 * 每一步沿主軸前進 1 格，其他軸按比例前進（3D Bresenham）。
 *
 * 「上下放」開關（作者定的，2026-11-08）：打開時不管方向模式和視線角度，一律正上或正下
 * （抬頭往上、其他往下；放方塊時第一格是實心的會再反過來，見 shouldReverse）。
 * 關掉時水平模式一律橫著長、立體模式最陡到 45° 斜線，低頭看腳邊放也不會長成柱子；
 * 自由模式本來就完全照視線，不受影響。以前水平模式抬頭或低頭超過 75° 會自動改成垂直，
 * 立體模式超過 67.5° 也是，看腳邊放時常常意外長出柱子。
 * @param {Vec3} view 視線方向
 * @param {string} mode DirectionMode
 * @param {boolean} [vertical] 「上下放」開關
 * @returns {Vec3}
 */
export function stepFromView(view, mode, vertical = false) {
  const pitch = pitchOf(view);
  const up = pitch > 0 ? 1 : -1;
  if (vertical) return { x: 0, y: up, z: 0 };

  if (mode === DirectionMode.Free) {
    const m = Math.max(Math.abs(view.x), Math.abs(view.y), Math.abs(view.z));
    if (m === 0) return { x: 1, y: 0, z: 0 };
    return { x: view.x / m, y: view.y / m, z: view.z / m };
  }

  const h = snapHorizontal(view);
  if (mode === DirectionMode.Snap3D && Math.abs(pitch) >= DIAGONAL_PITCH) return { x: h.x, y: up, z: h.z };
  return { x: h.x, y: 0, z: h.z };
}

/**
 * 第 i 步的座標。
 * @param {Vec3} origin
 * @param {Vec3} step
 * @param {number} i
 * @returns {Vec3}
 */
export function pointAt(origin, step, i) {
  return {
    x: origin.x + roundHalfAway(step.x * i),
    y: origin.y + roundHalfAway(step.y * i),
    z: origin.z + roundHalfAway(step.z * i),
  };
}

/**
 * 從第一顆方塊開始，算出後面要處理的座標（作者定的算法，2026-11-05）。
 * 第一顆是第 0 步，也算在範圍內；間隔 gap 表示中間空 gap 格，所以每 gap + 1 步一顆。
 * 例如範圍 20、間隔 2：第 0、3、6…18 步，連第一顆共 7 顆。
 * @param {Vec3} origin 第一顆方塊的座標
 * @param {Vec3} step stepFromView 的結果
 * @param {number} range 範圍：幾格內，含第一顆
 * @param {number} gap 中間空幾格
 * @returns {Vec3[]}
 */
export function linePositions(origin, step, range, gap) {
  const stride = gap + 1;
  const out = [];
  for (let k = stride; k < range; k += stride) out.push(pointAt(origin, step, k));
  return out;
}

/**
 * 放方塊時，線要不要反過來長（作者定的，2026-11-06）。
 * 水平和斜線一律順著視線往前，路上的方塊（包括點到的那顆）照「可以蓋掉」的設定蓋掉。
 * 只有線的第一步是正上、正下，而且那一格是實心的方塊時才反過來：
 * 看著地面放 → 往上長柱子；看著天花板放 → 往下垂。貼著洞壁往下放、下面是空的，就照視線往下。
 * 以前是靠「剛剛右鍵點到哪顆」判斷，水平時也會反過來，而且這筆紀錄偶爾對不上，
 * 所以對著前方的方塊放時，有時往前、有時往背後長。
 * @param {Vec3} origin 第一顆方塊
 * @param {Vec3} step
 * @param {boolean} firstIsSolid 線的第一格是不是實心的方塊（不是空氣、也不是液體）
 */
export function shouldReverse(origin, step, firstIsSolid) {
  if (!firstIsSolid) return false;
  const first = pointAt(origin, step, 1);
  return first.x === origin.x && first.z === origin.z && first.y !== origin.y;
}

/**
 * @param {Vec3} v
 * @returns {Vec3}
 */
export function negate(v) {
  return { x: -v.x || 0, y: -v.y || 0, z: -v.z || 0 };
}

/**
 * 把數字限制在範圍內並取整數；無法解析時回傳 undefined。
 * @param {unknown} value
 * @param {number} min
 * @param {number} max
 */
export function parseIntInRange(value, min, max) {
  const n = typeof value === 'number' ? value : Number.parseInt(String(value ?? '').trim(), 10);
  if (!Number.isFinite(n)) return undefined;
  return Math.min(max, Math.max(min, Math.trunc(n)));
}

/**
 * 用中文描述方向，例如「東北」「正上方」「東（往上斜）」。
 * Minecraft 的座標：+x 東、-x 西、+z 南、-z 北、+y 上。
 * @param {Vec3} step
 * @param {string} mode
 */
export function describeDirection(step, mode) {
  const ns = step.z < -0.38 ? '北' : step.z > 0.38 ? '南' : '';
  const ew = step.x > 0.38 ? '東' : step.x < -0.38 ? '西' : '';
  const horizontal = ew && ns ? ew + ns : ew || ns;
  const vertical = step.y > 0.38 ? '上' : step.y < -0.38 ? '下' : '';
  let text;
  if (!horizontal) text = vertical === '上' ? '正上方' : vertical === '下' ? '正下方' : '前方';
  else if (!vertical) text = horizontal;
  else text = `${horizontal}（往${vertical}斜）`;
  return mode === DirectionMode.Free ? `${text}，自由角度` : text;
}

/**
 * 兩格高的方塊（門、高草、向日葵等）的上半部要放什麼；沒有上半部就回傳 undefined。
 * 原版的上半部在放下時就有了，照抄上面那一格。Asuka tech 的門用自己的狀態分上下半，
 * 上半是放下之後才由它的腳本補上，這時可能還沒出現，所以直接算（2026-11-04）。
 * @param {BlockPermutation} base 下半部
 * @param {BlockPermutation | undefined} above 上面那一格
 * @returns {BlockPermutation | undefined}
 */
export function topPermutationOf(base, above) {
  if (base.getState('upper_block_bit') === false) {
    const same = above && above.type.id === base.type.id && above.getState('upper_block_bit') === true;
    return same ? above : undefined;
  }
  if (base.getState('asukatech:upper') === false) return base.withState('asukatech:upper', true);
  return undefined;
}
