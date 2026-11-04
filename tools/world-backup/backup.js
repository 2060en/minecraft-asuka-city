// 備份世界並更新雲端地圖：雙擊 backup.bat，或執行 node backup.js
//
// 流程：
//   1. 確認 Minecraft 已經關閉
//   2. 用 restic 建立快照（備份到 Google Drive）
//   3. 用 uNmINeD 渲染整張網頁地圖；設定檔的 map.enabled 不是 true 就跳過 3、4
//   4. 把有變動的圖磚上傳到 Cloudflare R2
//   5. 在 docs/backup-log.md 加一行紀錄
//
// 參數：
//   --note "文字"   這次備份的備註（沒給就會問）
//   --skip-backup   不做 restic 備份，只更新地圖
//   --skip-map      只做 restic 備份，不更新地圖
//   --publish-only  不備份、不渲染，只重新上傳（上次上傳失敗時用）

import { existsSync, appendFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { loadConfig, rcloneConfigFile, resticEnv, unminedRenderArgs } from './lib/config.js';
import { ask, runVisible, runLines, isRunning } from './lib/run.js';
import { publishMap } from './lib/publish.js';
import { formatBytes, reportRow, REPORT_HEADER } from './lib/report.js';

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
 * @param {import('./lib/config.js').Config} config
 */
async function backupWithRestic(config) {
  const env = resticEnv(config);
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
 * @param {import('./lib/config.js').Config} config
 * @param {string} staging
 */
async function uploadWithRclone(config, staging) {
  const { exe, remote, extraArgs } = config.rclone;
  const common = ['--config', rcloneConfigFile, '--transfers', '16', '--checkers', '16', '--s3-no-check-bucket', ...extraArgs];
  if (existsSync(join(staging, 'tiles'))) {
    await runVisible(exe, ['copy', join(staging, 'tiles'), `${remote}/tiles`, '--ignore-existing', '--header-upload', 'Cache-Control: private, max-age=31536000, immutable', '--stats-one-line', '--stats', '10s', '--stats-log-level', 'NOTICE', ...common]);
  }
  await runVisible(exe, ['copy', join(staging, 'snapshots'), `${remote}/snapshots`, '--header-upload', 'Cache-Control: private, max-age=31536000, immutable', ...common]);
  await runVisible(exe, ['copyto', join(staging, 'index.json'), `${remote}/index.json`, '--header-upload', 'Cache-Control: no-cache', ...common]);
}

async function main() {
  const config = loadConfig();
  const args = parseArgs(process.argv.slice(2));
  if (!config.map.enabled) {
    if (args.skipBackup) {
      console.error('設定檔的 map.enabled 不是 true，地圖還沒啟用，--skip-backup 和 --publish-only 沒有事情可做。');
      process.exit(1);
    }
    args.skipMap = true;
  }

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
    console.log(args.skipMap ? '\nrestic 備份' : '\n[1/3] restic 備份');
    backup = await backupWithRestic(config);
    console.log(`  完成：快照 ${backup.snapshot}，世界 ${formatBytes(backup.worldBytes)}，新增 ${formatBytes(backup.addedBytes)}`);
  }

  /** @type {import('./lib/publish.js').SnapshotSummary | undefined} */
  let map;
  /** @type {unknown} */
  let mapError;
  if (!args.skipMap) {
    try {
      if (!args.publishOnly) {
        console.log('\n[2/3] uNmINeD 渲染地圖（約 1～3 分鐘，這段不會顯示進度）');
        mkdirSync(config.map.renderDir, { recursive: true });
        await runVisible(config.unmined.exe, unminedRenderArgs(config));
      }
      console.log('\n[3/3] 上傳地圖（只傳有變動的圖磚）');
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
      if (config.map.url) console.log(`  地圖網址：${config.map.url}`);
    } catch (error) {
      // restic 備份已經成功的話，地圖失敗不該讓這次備份看起來像沒做
      mapError = error;
    }
  }

  if (!args.skipBackup || map) {
    if (!existsSync(config.reportFile)) {
      mkdirSync(dirname(config.reportFile), { recursive: true });
      writeFileSync(config.reportFile, REPORT_HEADER);
    }
    appendFileSync(config.reportFile, reportRow({ date: startedAt, note, backup: args.skipBackup ? undefined : backup, map }));
  }
  if (mapError) {
    console.error(`\n地圖失敗：${mapError instanceof Error ? mapError.message : mapError}`);
    if (!args.skipBackup) console.error(`世界已經備份好了（快照 ${backup.snapshot}），只有雲端地圖這次沒更新，下次備份會一起補上。`);
    console.error('世界資料夾沒有被更動。把這個畫面截圖給 Claude 看就好。');
    process.exit(1);
  }
  console.log(`\n完成。紀錄寫在 ${config.reportFile}，下次請 Claude 一起提交。`);
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  console.error('這次備份沒有完成，世界資料夾沒有被更動。把這個畫面截圖給 Claude 看就好。');
  process.exit(1);
});
