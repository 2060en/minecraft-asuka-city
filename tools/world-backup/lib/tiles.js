// uNmINeD 網頁地圖的圖磚處理。純計算，不碰檔案系統，方便測試。
//
// uNmINeD 輸出的圖磚路徑：tiles/zoom.{z}/{x/10 取整}/{y/10 取整}/tile.{x}.{y}.{副檔名}
// 每張圖磚 256 × 256 像素；zoom 0 是 1 格 1 像素，zoom -1 是 2 格 1 像素，zoom 1 是 1 格 2 像素。
// x 是東西方向（遊戲的 X 座標），y 是南北方向（遊戲的 Z 座標）。
// tiles 底下還有 uNmINeD 自己用的 zoom.-1/metadata/k.*.csv，不是圖磚，不上傳。

/**
 * @typedef {object} TileRef
 * @property {number} zoom
 * @property {number} x
 * @property {number} y
 * @property {string} ext
 */

const TILE_PATTERN = /^tiles\/zoom\.(-?\d+)\/(-?\d+)\/(-?\d+)\/tile\.(-?\d+)\.(-?\d+)\.([a-z0-9]+)$/i;

/**
 * 解析圖磚的相對路徑（用 / 分隔）；不是圖磚就回傳 undefined。
 * @param {string} relPath
 * @returns {TileRef | undefined}
 */
export function parseTilePath(relPath) {
  const m = TILE_PATTERN.exec(relPath);
  if (!m) return undefined;
  const [, zoom, xd, yd, x, y, ext] = m;
  const tile = { zoom: Number(zoom), x: Number(x), y: Number(y), ext: ext.toLowerCase() };
  // 資料夾編號要和檔名對得上，避免誤認
  if (Math.floor(tile.x / 10) !== Number(xd) || Math.floor(tile.y / 10) !== Number(yd)) return undefined;
  return tile;
}

/**
 * 讀出 unmined.map.properties.js 裡的設定值（只讀數字、字串、布林）。
 * @param {string} source 檔案內容
 * @returns {Record<string, string | number | boolean>}
 */
export function parseMapProperties(source) {
  /** @type {Record<string, string | number | boolean>} */
  const props = {};
  const re = /^\s*([A-Za-z]\w*)\s*:\s*("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|true|false)\s*,?\s*$/gm;
  for (const m of source.matchAll(re)) {
    const [, key, raw] = m;
    if (raw === 'true' || raw === 'false') props[key] = raw === 'true';
    else if (raw.startsWith('"')) props[key] = JSON.parse(raw);
    else props[key] = Number(raw);
  }
  return props;
}

/** 檢視網頁用得到的地圖設定 */
const VIEWER_PROPERTIES = [
  'minZoom',
  'maxZoom',
  'defaultZoom',
  'imageFormat',
  'minRegionX',
  'minRegionZ',
  'maxRegionX',
  'maxRegionZ',
  'worldName',
  'background',
];

/**
 * @param {Record<string, string | number | boolean>} props
 */
export function pickViewerProperties(props) {
  /** @type {Record<string, string | number | boolean>} */
  const out = {};
  for (const key of VIEWER_PROPERTIES) if (key in props) out[key] = props[key];
  return out;
}

/**
 * 雲端上存放圖磚的路徑。
 * @param {string} hash
 * @param {string} ext
 */
export function tileObjectKey(hash, ext) {
  return `tiles/${hash.slice(0, 2)}/${hash}.${ext}`;
}

/** 相距不到這麼多格的地方算同一塊區域 */
const AREA_GRID = 4096;

/**
 * @typedef {object} MapArea
 * @property {number} minX
 * @property {number} maxX
 * @property {number} minZ
 * @property {number} maxZ
 * @property {number} tiles 這塊區域的圖磚數
 */

/**
 * 把地圖分成幾塊互相分開的區域，圖磚最多的排在最前面（世界的主體）。
 * 飛到或傳送到遠處留下的零星區塊（作者的世界最遠到座標 3000 萬）會自成一塊，不會把主體的範圍撐大。
 * 以最接近 zoom 0 的等級計算。
 * @param {{ tile: TileRef }[]} tiles
 * @returns {MapArea[]}
 */
export function mapAreas(tiles) {
  if (tiles.length === 0) return [];
  const zoom = tiles.reduce((best, { tile }) => (Math.abs(tile.zoom) < Math.abs(best) ? tile.zoom : best), tiles[0].tile.zoom);
  const size = 256 / 2 ** zoom;
  /** @type {Map<string, MapArea>} */
  const cells = new Map();
  for (const { tile } of tiles) {
    if (tile.zoom !== zoom) continue;
    const key = `${Math.floor((tile.x * size) / AREA_GRID)},${Math.floor((tile.y * size) / AREA_GRID)}`;
    const cell = cells.get(key) ?? { minX: Infinity, maxX: -Infinity, minZ: Infinity, maxZ: -Infinity, tiles: 0 };
    cell.minX = Math.min(cell.minX, tile.x * size);
    cell.maxX = Math.max(cell.maxX, (tile.x + 1) * size);
    cell.minZ = Math.min(cell.minZ, tile.y * size);
    cell.maxZ = Math.max(cell.maxZ, (tile.y + 1) * size);
    cell.tiles++;
    cells.set(key, cell);
  }
  /** @type {Set<string>} */
  const seen = new Set();
  /** @type {MapArea[]} */
  const areas = [];
  for (const start of cells.keys()) {
    if (seen.has(start)) continue;
    seen.add(start);
    const stack = [start];
    const area = { minX: Infinity, maxX: -Infinity, minZ: Infinity, maxZ: -Infinity, tiles: 0 };
    while (stack.length > 0) {
      const key = /** @type {string} */ (stack.pop());
      const cell = /** @type {MapArea} */ (cells.get(key));
      area.minX = Math.min(area.minX, cell.minX);
      area.maxX = Math.max(area.maxX, cell.maxX);
      area.minZ = Math.min(area.minZ, cell.minZ);
      area.maxZ = Math.max(area.maxZ, cell.maxZ);
      area.tiles += cell.tiles;
      const [cx, cz] = key.split(',').map(Number);
      for (let dx = -1; dx <= 1; dx++) {
        for (let dz = -1; dz <= 1; dz++) {
          const next = `${cx + dx},${cz + dz}`;
          if (cells.has(next) && !seen.has(next)) {
            seen.add(next);
            stack.push(next);
          }
        }
      }
    }
    areas.push(area);
  }
  return areas.sort((a, b) => b.tiles - a.tiles);
}

/**
 * @typedef {object} Manifest
 * @property {number} version
 * @property {string} id
 * @property {string} createdAt ISO 時間
 * @property {string} note
 * @property {string} restic restic 快照編號（沒有就是空字串）
 * @property {string} ext 圖磚副檔名
 * @property {Record<string, string | number | boolean>} properties
 * @property {MapArea[]} areas 地圖上互相分開的區域，第一塊是世界的主體
 * @property {Record<string, Record<string, string>>} tiles zoom → "x,y" → 雜湊值
 */

/**
 * 組出一次備份的地圖清單。
 * @param {object} input
 * @param {string} input.id
 * @param {string} input.createdAt
 * @param {string} input.note
 * @param {string} input.restic
 * @param {Record<string, string | number | boolean>} input.properties
 * @param {{ tile: TileRef, hash: string }[]} input.tiles
 * @returns {Manifest}
 */
export function buildManifest({ id, createdAt, note, restic, properties, tiles }) {
  /** @type {Record<string, Record<string, string>>} */
  const byZoom = {};
  const exts = new Set();
  const sorted = [...tiles].sort((a, b) => a.tile.zoom - b.tile.zoom || a.tile.y - b.tile.y || a.tile.x - b.tile.x);
  for (const { tile, hash } of sorted) {
    (byZoom[tile.zoom] ??= {})[`${tile.x},${tile.y}`] = hash;
    exts.add(tile.ext);
  }
  if (exts.size > 1) throw new Error(`圖磚有好幾種格式：${[...exts].join('、')}，請清空渲染資料夾後重新渲染`);
  const ext = [...exts][0] ?? String(properties.imageFormat ?? 'png');
  return { version: 1, id, createdAt, note, restic, ext, properties: pickViewerProperties(properties), areas: mapAreas(tiles), tiles: byZoom };
}

/**
 * 依照時間產生備份編號，例如 2026-11-01-2130；同一分鐘有重複時加上 -2、-3。
 * @param {Date} date
 * @param {Set<string>} existing
 */
export function snapshotId(date, existing) {
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  const base = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}`;
  if (!existing.has(base)) return base;
  for (let i = 2; ; i++) if (!existing.has(`${base}-${i}`)) return `${base}-${i}`;
}
