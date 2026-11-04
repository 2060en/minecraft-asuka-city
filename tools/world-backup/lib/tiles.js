// uNmINeD 網頁地圖的圖磚處理。純計算，不碰檔案系統，方便測試。
//
// uNmINeD 輸出的圖磚路徑：tiles/zoom.{z}/{x/10 取整}/{y/10 取整}/tile.{x}.{y}.{副檔名}
// 每張圖磚 256 × 256 像素；zoom 0 是 1 格 1 像素，zoom -1 是 2 格 1 像素，zoom 1 是 1 格 2 像素。
// x 是東西方向（遊戲的 X 座標），y 是南北方向（遊戲的 Z 座標）。

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
  'centerX',
  'centerZ',
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

/**
 * @typedef {object} Manifest
 * @property {number} version
 * @property {string} id
 * @property {string} createdAt ISO 時間
 * @property {string} note
 * @property {string} restic restic 快照編號（沒有就是空字串）
 * @property {string} ext 圖磚副檔名
 * @property {Record<string, string | number | boolean>} properties
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
  return { version: 1, id, createdAt, note, restic, ext, properties: pickViewerProperties(properties), tiles: byZoom };
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
