// 還原備份：雙擊 restore.bat，或執行 node restore.js
//
// 只還原到新的資料夾（%USERPROFILE%/AsukaRestore/<時間>），不會碰世界資料夾。
// 還原完會和目前的世界逐檔比對；世界在備份之後玩過的話，有差異是正常的。
//
// 參數：
//   快照編號   要還原哪一份（沒給就會問，直接按 Enter 是最新的）

import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { loadConfig, resticEnv } from './lib/config.js';
import { ask, expandEnv, isRunning, runVisible } from './lib/run.js';
import { compareFolders, snapshotPath } from './lib/restore.js';

/** @param {Date} date */
function timestamp(date) {
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

async function main() {
  const config = loadConfig();
  const env = resticEnv(config);

  console.log('雲端上的備份：\n');
  await runVisible(config.restic.exe, ['snapshots', '--tag', 'minecraft'], env);
  const answer = process.argv[2] ?? (await ask('\n要還原哪一份？輸入左邊的 ID，直接按 Enter 是最新的：'));
  const snapshot = answer || 'latest';

  const target = join(resolve(expandEnv('%USERPROFILE%/AsukaRestore')), timestamp(new Date()));
  mkdirSync(target, { recursive: true });
  console.log(`\n還原到 ${target}\n`);
  await runVisible(config.restic.exe, ['restore', `${snapshot}:${snapshotPath(config.worldPath)}`, '--tag', 'minecraft', '--target', target], env);

  if (isRunning(config.minecraftProcesses)) {
    console.log('\nMinecraft 開著，跳過和世界資料夾的比對。');
  } else {
    console.log('\n和目前的世界逐檔比對…');
    const result = await compareFolders(target, config.worldPath);
    console.log(`  一模一樣：${result.same} 個檔案`);
    console.log(`  內容不同：${result.different.length} 個`);
    console.log(`  世界裡有、備份裡沒有：${result.missing.length} 個`);
    console.log(`  備份裡有、世界裡沒有：${result.extra.length} 個`);
    for (const file of [...result.different, ...result.missing, ...result.extra].slice(0, 20)) console.log(`    ${file}`);
    if (result.different.length + result.missing.length + result.extra.length > 0) {
      console.log('  世界在這次備份之後玩過的話，有差異是正常的。');
    }
  }

  console.log(`\n完成。還原的世界在 ${target}，世界資料夾沒有被更動。`);
  console.log('要拿回遊戲裡用：先關掉 Minecraft，把這個資料夾整個複製到 minecraftWorlds 底下，換個資料夾名稱，遊戲裡會多出一個世界。');
  console.log('不需要的話，這個資料夾可以直接刪掉。');
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  console.error('這次還原沒有完成，世界資料夾沒有被更動。把這個畫面截圖給 Claude 看就好。');
  process.exit(1);
});
