// 一次性設定：讓 rclone 連到 Google Drive。雙擊 setup-gdrive.bat。
//
// Client ID 與密鑰由作者貼進這個視窗，rclone 存在 %USERPROFILE%/.config/asuka/rclone.conf（不在 repo 裡）。
// rclone 設定完會把存取權杖印出來，所以不顯示它的標準輸出。

import { spawnSync } from 'node:child_process';
import { createInterface } from 'node:readline/promises';
import { rcloneConfigFile } from './lib/config.js';
import { findExe } from './lib/run.js';

const REMOTE = 'gdrive';
const env = { ...process.env, RCLONE_CONFIG: rcloneConfigFile };

async function main() {
  const rclone = findExe('rclone');
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const remotes = spawnSync(rclone, ['listremotes'], { encoding: 'utf8', env });
  if (remotes.error) throw new Error(`找不到 rclone：${remotes.error.message}`);
  const exists = remotes.stdout.split(/\r?\n/).includes(`${REMOTE}:`);

  if (exists) {
    const answer = (await rl.question(`rclone 已經有 ${REMOTE} 這個設定，要換掉嗎？（y／n）：`)).trim().toLowerCase();
    if (answer !== 'y') {
      rl.close();
      console.log('沒有更動。');
      return;
    }
  }
  const clientId = (await rl.question('貼上 Client ID 後按 Enter：')).trim();
  const clientSecret = (await rl.question('貼上 Client secret（用戶端密鑰）後按 Enter：')).trim();
  rl.close();
  if (!clientId.endsWith('.apps.googleusercontent.com')) {
    throw new Error('Client ID 應該以 .apps.googleusercontent.com 結尾，請確認沒有貼反。沒有更動任何設定。');
  }
  if (!clientSecret) throw new Error('沒有貼上密鑰。沒有更動任何設定。');

  if (exists) spawnSync(rclone, ['config', 'delete', REMOTE], { stdio: 'inherit', env });
  console.log('\n瀏覽器會跳出來，請登入有 5 TB 空間的 Google 帳號並同意授權。\n');
  const create = spawnSync(rclone, ['config', 'create', REMOTE, 'drive', `client_id=${clientId}`, `client_secret=${clientSecret}`, 'scope=drive.file'], { stdio: ['inherit', 'ignore', 'inherit'], env });
  if (create.status !== 0) throw new Error(`rclone 設定失敗（結束碼 ${create.status}）`);

  console.log('\n設定完成，這個帳號的 Google Drive 空間：\n');
  spawnSync(rclone, ['about', `${REMOTE}:`], { stdio: 'inherit', env });
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  process.exit(1);
});
