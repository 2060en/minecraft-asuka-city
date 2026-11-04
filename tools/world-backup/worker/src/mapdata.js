// 地圖清單的計算：座標換算、找出某個座標周圍的圖磚、比較兩次備份的差異。純計算，方便測試。

export const TILE_SIZE = 256;

/**
 * @typedef {object} Manifest
 * @property {string} id
 * @property {string} createdAt
 * @property {string} note
 * @property {string} ext
 * @property {Record<string, string | number | boolean>} properties
 * @property {{ minX: number, maxX: number, minZ: number, maxZ: number, tiles: number }[]} areas 互相分開的區域，第一塊是世界的主體
 * @property {Record<string, Record<string, string>>} tiles zoom → "x,y" → 雜湊值
 */

/**
 * 每張圖磚涵蓋幾格方塊。zoom 0 是 256 格，zoom -1 是 512 格，zoom 1 是 128 格。
 * @param {number} zoom
 */
export function blocksPerTile(zoom) {
  return TILE_SIZE / 2 ** zoom;
}

/**
 * 圖磚涵蓋的方塊範圍（含頭不含尾）。
 * @param {number} zoom
 * @param {number} x
 * @param {number} y
 */
export function tileBounds(zoom, x, y) {
  const size = blocksPerTile(zoom);
  return { minX: x * size, maxX: (x + 1) * size, minZ: y * size, maxZ: (y + 1) * size };
}

/**
 * 清單裡有圖磚的縮放等級（由小到大）。
 * @param {Manifest} manifest
 */
export function zoomLevels(manifest) {
  return Object.keys(manifest.tiles)
    .map(Number)
    .filter((z) => Object.keys(manifest.tiles[z]).length > 0)
    .sort((a, b) => a - b);
}

/**
 * 某個座標周圍的 2 × 2 張圖磚，讓座標落在四張圖的中間附近。
 * @param {number} blockX
 * @param {number} blockZ
 * @param {number} zoom
 * @returns {{ x: number, y: number, position: string }[]}
 */
export function tilesAround(blockX, blockZ, zoom) {
  const scale = 2 ** zoom;
  const x0 = Math.floor((blockX * scale - TILE_SIZE / 2) / TILE_SIZE);
  const y0 = Math.floor((blockZ * scale - TILE_SIZE / 2) / TILE_SIZE);
  return [
    { x: x0, y: y0, position: '左上（西北）' },
    { x: x0 + 1, y: y0, position: '右上（東北）' },
    { x: x0, y: y0 + 1, position: '左下（西南）' },
    { x: x0 + 1, y: y0 + 1, position: '右下（東南）' },
  ];
}

/**
 * 比較兩次備份在某個縮放等級的圖磚，把有變動的圖磚依相鄰關係合併成幾個區域。
 * @param {Manifest | undefined} before 較舊的備份；沒有時全部算新增
 * @param {Manifest} after
 * @param {number} zoom
 * @returns {{ minX: number, maxX: number, minZ: number, maxZ: number, centerX: number, centerZ: number, tiles: number }[]}
 *   依變動的圖磚數由多到少排序
 */
export function changedAreas(before, after, zoom) {
  const a = before?.tiles[zoom] ?? {};
  const b = after.tiles[zoom] ?? {};
  /** @type {Set<string>} */
  const changed = new Set();
  for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) if (a[key] !== b[key]) changed.add(key);

  /** @type {Set<string>} */
  const seen = new Set();
  const areas = [];
  for (const start of changed) {
    if (seen.has(start)) continue;
    const stack = [start];
    seen.add(start);
    let minTX = Infinity;
    let minTY = Infinity;
    let maxTX = -Infinity;
    let maxTY = -Infinity;
    let count = 0;
    while (stack.length > 0) {
      const key = /** @type {string} */ (stack.pop());
      const [x, y] = key.split(',').map(Number);
      count++;
      minTX = Math.min(minTX, x);
      minTY = Math.min(minTY, y);
      maxTX = Math.max(maxTX, x);
      maxTY = Math.max(maxTY, y);
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          const next = `${x + dx},${y + dy}`;
          if (changed.has(next) && !seen.has(next)) {
            seen.add(next);
            stack.push(next);
          }
        }
      }
    }
    const size = blocksPerTile(zoom);
    const area = { minX: minTX * size, maxX: (maxTX + 1) * size, minZ: minTY * size, maxZ: (maxTY + 1) * size };
    areas.push({ ...area, centerX: Math.floor((area.minX + area.maxX) / 2), centerZ: Math.floor((area.minZ + area.maxZ) / 2), tiles: count });
  }
  return areas.sort((p, q) => q.tiles - p.tiles);
}
