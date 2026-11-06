// 還原用到的計算：世界在快照裡的路徑、比對還原結果和世界資料夾。

import { createHash } from 'node:crypto';
import { createReadStream, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

/**
 * 世界資料夾在 restic 快照裡的路徑。restic 在 Windows 上把 C:\Users 存成 /C/Users。
 * @param {string} worldPath
 */
export function snapshotPath(worldPath) {
  const path = worldPath.replace(/\\/g, '/');
  return path.replace(/^([A-Za-z]):\//, '/$1/');
}

/**
 * 從 `restic snapshots <編號> --json` 的結果取出要還原的那一份，和它在快照裡的資料夾。
 * 舊的手動備份是從別的資料夾歸檔的（見 README「舊的手動備份」），路徑和現在的世界不同，所以要照快照自己記的路徑還原。
 * @param {string} json
 * @returns {{ id: string, shortId: string, time: string, path: string }}
 */
export function parseSnapshot(json) {
  const list = /** @type {{ id: string, short_id: string, time: string, paths: string[] }[]} */ (JSON.parse(json || '[]'));
  if (list.length === 0) throw new Error('找不到這一份備份，請確認輸入的 ID。');
  const chosen = [...list].sort((a, b) => a.time.localeCompare(b.time))[list.length - 1];
  if (chosen.paths.length !== 1) throw new Error(`這份備份有 ${chosen.paths.length} 個資料夾，不知道要還原哪一個。`);
  return { id: chosen.id, shortId: chosen.short_id, time: chosen.time, path: snapshotPath(chosen.paths[0]) };
}

/**
 * 快照裡的資料夾是不是現在的世界資料夾（Windows 不分大小寫）。
 * @param {string} path snapshotPath 轉過的路徑
 * @param {string} worldPath
 */
export function isCurrentWorld(path, worldPath) {
  return path.toLowerCase() === snapshotPath(worldPath).toLowerCase();
}

/** @param {string} dir */
function listFiles(dir) {
  return readdirSync(dir, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => relative(dir, join(entry.parentPath, entry.name)).replace(/\\/g, '/'))
    .sort();
}

/** @param {string} file */
async function hashFile(file) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}

/**
 * 逐檔比對還原結果和世界資料夾，大小一樣的檔案也會比對內容。只讀不寫。
 * @param {string} restored 還原出來的資料夾
 * @param {string} world 世界資料夾
 * @returns {Promise<{ same: number, different: string[], missing: string[], extra: string[] }>}
 *   missing 是世界裡有、備份裡沒有；extra 是備份裡有、世界裡沒有
 */
export async function compareFolders(restored, world) {
  const restoredFiles = listFiles(restored);
  const worldFiles = new Set(listFiles(world));
  const result = { same: 0, different: /** @type {string[]} */ ([]), missing: /** @type {string[]} */ ([]), extra: /** @type {string[]} */ ([]) };
  for (const file of restoredFiles) {
    if (!worldFiles.delete(file)) {
      result.extra.push(file);
      continue;
    }
    const a = join(restored, file);
    const b = join(world, file);
    const equal = statSync(a).size === statSync(b).size && (await hashFile(a)) === (await hashFile(b));
    if (equal) result.same += 1;
    else result.different.push(file);
  }
  result.missing = [...worldFiles];
  return result;
}
