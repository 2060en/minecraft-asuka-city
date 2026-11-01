// 備份世界並更新雲端地圖：雙擊 backup.bat，或執行 node backup.js
//
// 流程：
//   1. 確認 Minecraft 已經關閉
//   2. 用 restic 建立快照（備份到 Google Drive）
//   3. 用 uNmINeD 渲染網頁地圖（只重畫有變動的區域）
//   4. 把有變動的圖磚上傳到 Cloudflare R2
//   5. 在 docs/backup-log.md 加一行紀錄
//
// 參數：
//   --note "文字"   這次備份的備註（沒給就會問）
//   --skip-backup   不做 restic 備份，只更新地圖
//   --skip-map      只做 restic 備份，不更新地圖
//   --publish-only  不備份、不渲染，只重新上傳（上次上傳失敗時用）

import { existsSync, readFileSync, appendFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline/promises';
import { runVisible, runLines, isRunning, expandEnv } from './lib/run.js';
import { publishMap } from './lib/publish.js';
import { formatBytes, reportRow, REPORT_HEADER } from './lib/report.js';

const here = dirname(fileURLToPath(import.meta.url));

/**
 * @typedef {object} Config
 * @property {string} worldPath
 * @property {string[]} minecraftProcesses
 * @property {{ exe: string, repository: string, passwordFile: string, forget: string[] }} restic
 * @property {{ exe: string, extraArgs: string[] }} unmined
 * @property {{ exe: string, remote: string, extraArgs: string[] }} rclone
 * @property {{ renderDir: string, stateDir: string }} map
 * @property {string} reportFile
 */

/** @returns {Config} */
function loadConfig() {
  const file = join(here, 'config.json');
  if (!existsSync(file)) {
    console.error('找不到 config.json。請把 config.example.json 複製成 config.json，填入路徑。');
    process.exit(1);
  }
  /** @type {Config} */
  const config = JSON.parse(readFileSync(file, 'utf8'));
  const path = (/** @type {string} */ p) => resolve(here, expandEnv(p));
  config.worldPath = path(config.worldPath);
  config.restic.passwordFile = config.restic.passwordFile ? path(config.restic.passwordFile) : '';
  config.map.renderDir = path(config.map.renderDir);
  config.map.stateDir = path(config.map.stateDir);
  config.reportFile = path(config.reportFile);
  config.restic.exe = expandEnv(config.restic.exe);
  config.unmined.exe = expandEnv(config.unmined.exe);
  config.rclone.exe = expandEnv(config.rclone.exe);
  return config;
}

/** @param {string[]} argv */
function parseArgs(argv) {
  const flags = new Set(argv.filter((a) => a.startsWith('--') && a !== '--note'));
  const noteIndex = argv.indexOf('--note');
  return {
    note: noteIndex >= 0 ? argv[noteIndex + 1] ?? '' : undefined,
    skipBackup: flags.has('--skip-backup') || flags.has('--publish-only'),
    skipMap: flags.has('--skip-map'),
    publishOnly: flags.has('--publish-only'),
  };
}

/**
 * restic 備份，回傳快照編號與大小。
 * @param {Config} config
 */
async function backupWithRestic(config) {
  const env = { RESTIC_REPOSITORY: config.restic.repository, ...(config.restic.passwordFile ? { RESTIC_PASSWORD_FILE: config.restic.passwordFile } : {}) };
  /** @type {any} */
  let summary;
  let lastPercent = -1;
  await runLines(
    config.restic.exe,
    ['backup', config.worldPath, '--tag', 'minecraft', '--json'],
    (line) => {
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        console.log(line);
        return;
      }
      if (message.message_type === 'status') {
        const percent = Math.floor((message.percent_done ?? 0) * 100);
        if (percent !== lastPercent && percent % 10 === 0) console.log(`  備份中… ${percent}%`);
        lastPercent = percent;
      } else if (message.message_type === 'summary') {
        summary = message;
      } else if (message.message_type === 'error') {
        console.error(`  restic：${message.error?.message ?? line}`);
      }
    },
    env,
  );
  if (!summary) throw new Error('restic 沒有回報備份結果');
  if (config.restic.forget.length > 0) {
    console.log('清理過舊的快照…');
    await runVisible(config.restic.exe, ['forget', '--tag', 'minecraft', '--prune', ...config.restic.forget], env);
  }
  return {
    snapshot: String(summary.snapshot_id ?? '').slice(0, 8),
    worldBytes: Number(summary.total_bytes_processed ?? 0),
    addedBytes: Number(summary.data_added ?? 0),
  };
}

/**
 * 用 rclone 上傳：先傳圖磚，再傳這次的清單，最後才更新 index.json，
 * 這樣網頁永遠不會讀到還沒傳完的備份。
 * @param {Config} config
 * @param {string} staging
 */
async function uploadWithRclone(config, staging) {
  const { exe, remote, extraArgs } = config.rclone;
  const common = ['--transfers', '16', '--checkers', '16', '--s3-no-check-bucket', ...extraArgs];
  if (existsSync(join(staging, 'tiles'))) {
    await runVisible(exe, ['copy', join(staging, 'tiles'), `${remote}/tiles`, '--ignore-existing', '--header-upload', 'Cache-Control: private, max-age=31536000, immutable', '--stats-one-line', '--stats', '10s', ...common]);
  }
  await runVisible(exe, ['copy', join(staging, 'snapshots'), `${remote}/snapshots`, '--header-upload', 'Cache-Control: private, max-age=31536000, immutable', ...common]);
  await runVisible(exe, ['copyto', join(staging, 'index.json'), `${remote}/index.json`, '--header-upload', 'Cache-Control: no-cache', ...common]);
}

/** @param {string} question */
async function ask(question) {
  if (!process.stdin.isTTY) return '';
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    return (await rl.question(question)).trim();
  } finally {
    rl.close();
  }
}

async function main() {
  const config = loadConfig();
  const args = parseArgs(process.argv.slice(2));

  if (!args.publishOnly && isRunning(config.minecraftProcesses)) {
    console.error('Minecraft 還開著。請先關閉 Minecraft 再備份，避免備份到寫到一半的檔案。');
    process.exit(1);
  }
  if (!existsSync(config.worldPath)) {
    console.error(`找不到世界資料夾：${config.worldPath}`);
    process.exit(1);
  }

  const note = args.note ?? (await ask('這次備份的備註（例如「蓋好 AKQ 第二航廈」，可以留空直接按 Enter）：'));
  const startedAt = new Date();

  let backup = { snapshot: '', worldBytes: 0, addedBytes: 0 };
  if (!args.skipBackup) {
    console.log('\n[1/3] restic 備份');
    backup = await backupWithRestic(config);
    console.log(`  完成：快照 ${backup.snapshot}，世界 ${formatBytes(backup.worldBytes)}，新增 ${formatBytes(backup.addedBytes)}`);
  }

  /** @type {import('./lib/publish.js').SnapshotSummary | undefined} */
  let map;
  if (!args.skipMap) {
    if (!args.publishOnly) {
      console.log('\n[2/3] uNmINeD 渲染地圖');
      mkdirSync(config.map.renderDir, { recursive: true });
      await runVisible(config.unmined.exe, ['web', 'render', `--world=${config.worldPath}`, `--output=${config.map.renderDir}`, ...config.unmined.extraArgs]);
    }
    console.log('\n[3/3] 上傳地圖');
    map = await publishMap({
      renderDir: config.map.renderDir,
      stateDir: config.map.stateDir,
      note,
      restic: backup.snapshot,
      now: startedAt,
      upload: async (staging, newTiles) => {
        console.log(`  要上傳 ${newTiles} 張新圖磚`);
        await uploadWithRclone(config, staging);
      },
    });
    console.log(`  完成：地圖 ${map.id}，共 ${map.tiles} 張圖磚，新上傳 ${map.newTiles} 張`);
  }

  if (!existsSync(config.reportFile)) {
    mkdirSync(dirname(config.reportFile), { recursive: true });
    writeFileSync(config.reportFile, REPORT_HEADER);
  }
  appendFileSync(config.reportFile, reportRow({ date: startedAt, note, backup: args.skipBackup ? undefined : backup, map }));
  console.log(`\n已記錄到 ${config.reportFile}，記得 commit。`);
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  process.exit(1);
});
