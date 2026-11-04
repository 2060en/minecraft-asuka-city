// 把 uNmINeD 的網頁地圖整理成「圖磚共用」的格式，上傳到 Cloudflare R2。
//
// 雲端的資料：
//   index.json                  所有備份的清單（新的在前面）
//   snapshots/<備份編號>.json    這次備份的地圖清單：每張圖磚對應到哪個雜湊值
//   tiles/<前兩碼>/<雜湊值>.png   圖磚本身，內容一樣的圖磚只存一份
//
// 本機的狀態（stateDir）：
//   tilecache.json   每張圖磚的大小、修改時間、雜湊值，沒變的圖磚不用重算
//   uploaded.txt     已經上傳過的雜湊值
//   index.json       備份清單（和雲端的一樣）
//   staging/         這次要上傳的檔案，上傳成功後刪掉

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync, copyFileSync, appendFileSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { parseTilePath, parseMapProperties, buildManifest, tileObjectKey, snapshotId } from './tiles.js';

/** @typedef {import('./tiles.js').TileRef} TileRef */
/** @typedef {import('./tiles.js').Manifest} Manifest */

/**
 * @typedef {object} SnapshotSummary
 * @property {string} id
 * @property {string} createdAt
 * @property {string} note
 * @property {string} restic
 * @property {number} tiles 這次地圖的圖磚數
 * @property {number} newTiles 這次新上傳的圖磚數
 */

/**
 * @param {string} dir
 * @returns {string[]} 相對路徑（用 / 分隔）
 */
function walk(dir, root = dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return walk(path, root);
    return [relative(root, path).split(sep).join('/')];
  });
}

/**
 * @template T
 * @param {string} file
 * @param {T} fallback
 * @returns {T}
 */
function readJson(file, fallback) {
  if (!existsSync(file)) return fallback;
  return JSON.parse(readFileSync(file, 'utf8'));
}

/**
 * @param {string} file
 * @param {unknown} value
 */
function writeJson(file, value) {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(value));
}

/**
 * 掃描渲染資料夾，算出每張圖磚的雜湊值。大小和修改時間沒變的圖磚沿用上次的結果。
 * @param {string} renderDir
 * @param {string} stateDir
 * @returns {{ tile: TileRef, hash: string, file: string }[]}
 */
export function scanTiles(renderDir, stateDir) {
  const cacheFile = join(stateDir, 'tilecache.json');
  /** @type {Record<string, [number, number, string]>} */
  const cache = readJson(cacheFile, {});
  /** @type {Record<string, [number, number, string]>} */
  const nextCache = {};
  const out = [];
  for (const rel of walk(join(renderDir, 'tiles'))) {
    const relPath = `tiles/${rel}`;
    const tile = parseTilePath(relPath);
    if (!tile) continue;
    const file = join(renderDir, relPath);
    const { size, mtimeMs } = statSync(file);
    const cached = cache[relPath];
    let hash;
    if (cached && cached[0] === size && cached[1] === mtimeMs) {
      hash = cached[2];
    } else {
      hash = createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 20);
    }
    nextCache[relPath] = [size, mtimeMs, hash];
    out.push({ tile, hash, file });
  }
  writeJson(cacheFile, nextCache);
  return out;
}

/**
 * @param {string} stateDir
 * @returns {Set<string>}
 */
function loadUploaded(stateDir) {
  const file = join(stateDir, 'uploaded.txt');
  if (!existsSync(file)) return new Set();
  return new Set(readFileSync(file, 'utf8').split('\n').filter(Boolean));
}

/**
 * @typedef {object} PublishOptions
 * @property {string} renderDir uNmINeD 的輸出資料夾
 * @property {string} stateDir 本機狀態資料夾
 * @property {string} note 這次備份的備註
 * @property {string} restic restic 快照編號
 * @property {Date} [now]
 * @property {(staging: string, newTileCount: number) => Promise<void>} upload 把 staging 資料夾上傳到雲端
 */

/**
 * 準備並上傳這次備份的地圖。
 * @param {PublishOptions} options
 * @returns {Promise<SnapshotSummary>}
 */
export async function publishMap({ renderDir, stateDir, note, restic, now = new Date(), upload }) {
  const propsFile = join(renderDir, 'unmined.map.properties.js');
  if (!existsSync(propsFile)) throw new Error(`找不到 ${propsFile}，uNmINeD 的網頁地圖可能還沒渲染`);
  const properties = parseMapProperties(readFileSync(propsFile, 'utf8'));

  const tiles = scanTiles(renderDir, stateDir);
  if (tiles.length === 0) throw new Error(`${renderDir} 裡沒有圖磚`);

  /** @type {{ snapshots: SnapshotSummary[] }} */
  const index = readJson(join(stateDir, 'index.json'), { snapshots: [] });
  const id = snapshotId(now, new Set(index.snapshots.map((s) => s.id)));
  const manifest = buildManifest({ id, createdAt: now.toISOString(), note, restic, properties, tiles });

  const uploaded = loadUploaded(stateDir);
  const staging = join(stateDir, 'staging');
  rmSync(staging, { recursive: true, force: true });

  /** @type {Set<string>} */
  const fresh = new Set();
  for (const { hash, file } of tiles) {
    if (uploaded.has(hash) || fresh.has(hash)) continue;
    const target = join(staging, tileObjectKey(hash, manifest.ext));
    mkdirSync(dirname(target), { recursive: true });
    copyFileSync(file, target);
    fresh.add(hash);
  }

  /** @type {SnapshotSummary} */
  const summary = { id, createdAt: manifest.createdAt, note, restic, tiles: tiles.length, newTiles: fresh.size };
  const nextIndex = { snapshots: [summary, ...index.snapshots] };
  writeJson(join(staging, 'snapshots', `${id}.json`), manifest);
  writeJson(join(staging, 'index.json'), nextIndex);

  await upload(staging, fresh.size);

  // 上傳成功才更新本機狀態；失敗時重跑一次就好
  if (fresh.size > 0) appendFileSync(join(stateDir, 'uploaded.txt'), [...fresh].join('\n') + '\n');
  writeJson(join(stateDir, 'index.json'), nextIndex);
  rmSync(staging, { recursive: true, force: true });
  return summary;
}
