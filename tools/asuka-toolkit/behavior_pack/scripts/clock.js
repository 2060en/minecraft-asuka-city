// 遊戲時間的換算。純計算，不依賴 @minecraft/server。

/**
 * 一天中的時間換成大約的時鐘時間（0 刻 = 早上 6 點）。
 * @param {number} ticks
 */
export function clockText(ticks) {
  const total = (((ticks % 24000) + 24000) % 24000) / 1000 + 6;
  const hour = Math.floor(total) % 24;
  const minute = Math.floor((total % 1) * 60);
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

/**
 * 這個時間算不算白天（看得到太陽）。
 * @param {number} ticks
 */
export function isDaytime(ticks) {
  const t = ((ticks % 24000) + 24000) % 24000;
  return t < 12500 || t >= 23500;
}
