// 測試還原用到的計算：npm test（在 tools/world-backup 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, join, resolve } from 'node:path';
import { snapshotPath, compareFolders } from '../lib/restore.js';
import { rcloneConfigFile, resticEnv } from '../lib/config.js';

test('restic 的環境變數：rclone 的資料夾放在 PATH 最前面，沿用原本 PATH 的大小寫', () => {
  const rclone = resolve('tools', 'rclone.exe');
  const dir = resolve('tools');
  const config = { restic: { exe: 'restic', repository: 'rclone:gdrive:x', passwordFile: 'pw.txt', forget: [] }, rclone: { exe: rclone, remote: '', extraArgs: [] } };
  assert.deepEqual(resticEnv(config, { Path: 'old' }), {
    RESTIC_REPOSITORY: 'rclone:gdrive:x',
    RCLONE_CONFIG: rcloneConfigFile,
    RESTIC_PASSWORD_FILE: 'pw.txt',
    Path: `${dir}${delimiter}old`,
  });
  assert.equal(rcloneConfigFile.includes('AppData'), false, 'rclone 的設定不能放在 AppData 底下');
  const notFound = { ...config, rclone: { ...config.rclone, exe: 'rclone' } };
  assert.equal('Path' in resticEnv(notFound, { Path: 'old' }), false, '找不到 rclone 時不動 PATH');
});

test('世界資料夾在 restic 快照裡的路徑', () => {
  assert.equal(
    snapshotPath('C:\\Users\\ian\\AppData\\Roaming\\Minecraft Bedrock\\minecraftWorlds\\PXjOwjIpBg0='),
    '/C/Users/ian/AppData/Roaming/Minecraft Bedrock/minecraftWorlds/PXjOwjIpBg0=',
  );
  assert.equal(snapshotPath('/home/ian/world'), '/home/ian/world');
});

/** @param {Record<string, string>} files */
function folder(files) {
  const dir = mkdtempSync(join(tmpdir(), 'compare-'));
  for (const [name, content] of Object.entries(files)) {
    mkdirSync(join(dir, name, '..'), { recursive: true });
    writeFileSync(join(dir, name), content);
  }
  return dir;
}

test('比對兩個資料夾：一模一樣', async () => {
  const files = { 'level.dat': 'abc', 'db/000001.ldb': 'def' };
  const result = await compareFolders(folder(files), folder(files));
  assert.deepEqual(result, { same: 2, different: [], missing: [], extra: [] });
});

test('比對兩個資料夾：找出內容不同、少了、多了的檔案', async () => {
  const restored = folder({ 'level.dat': 'abc', 'db/changed.ldb': 'old', 'db/gone.ldb': 'x', 'sameSize.txt': 'aaa' });
  const world = folder({ 'level.dat': 'abc', 'db/changed.ldb': 'newer', 'db/new.ldb': 'y', 'sameSize.txt': 'bbb' });
  const result = await compareFolders(restored, world);
  assert.equal(result.same, 1);
  assert.deepEqual(result.different, ['db/changed.ldb', 'sameSize.txt'], '大小一樣但內容不同也要抓到');
  assert.deepEqual(result.extra, ['db/gone.ldb'], '備份裡有、世界裡沒有');
  assert.deepEqual(result.missing, ['db/new.ldb'], '世界裡有、備份裡沒有');
});
