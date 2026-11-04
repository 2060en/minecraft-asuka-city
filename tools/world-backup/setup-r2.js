// 一次性設定：讓 rclone 連到 Cloudflare R2（放地圖資料的地方）。雙擊 setup-r2.bat。
//
// 金鑰由作者貼進這個視窗，rclone 存在 %USERPROFILE%/.config/asuka/rclone.conf（不在 repo 裡）。
// rclone 設定完會把金鑰印出來，所以不顯示它的標準輸出。

import { spawnSync } from 'node:child_process';
import { createInterface } from 'node:readline/promises';
import { loadConfig, parseR2Endpoint, rcloneConfigFile } from './lib/config.js';

const env = { ...process.env, RCLONE_CONFIG: rcloneConfigFile };

async function main() {
  const config = loadConfig();
  const rclone = config.rclone.exe;
  const [REMOTE, BUCKET] = config.rclone.remote.split(':');
  const TEST_FILE = `${config.rclone.remote}/.setup-test`;
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
  const endpoint = parseR2Endpoint(config.rclone.r2Endpoint ?? (await rl.question('貼上 S3 API 的網址（https:// 開頭）後按 Enter：')));
  const accessKey = (await rl.question('貼上 Access Key ID 後按 Enter：')).trim();
  const secretKey = (await rl.question('貼上 Secret Access Key 後按 Enter：')).trim();
  rl.close();
  if (!endpoint) throw new Error('S3 API 的網址格式不對，應該長得像 https://<一串英數字>.r2.cloudflarestorage.com。沒有更動任何設定。');
  if (!/^[0-9a-f]{32}$/i.test(accessKey)) throw new Error('Access Key ID 應該是 32 個英數字，請確認沒有貼反。沒有更動任何設定。');
  if (!/^[0-9a-f]{64}$/i.test(secretKey)) throw new Error('Secret Access Key 應該是 64 個英數字，請確認沒有貼反。沒有更動任何設定。');

  if (exists) spawnSync(rclone, ['config', 'delete', REMOTE], { stdio: 'inherit', env });
  const create = spawnSync(
    rclone,
    ['config', 'create', REMOTE, 's3', 'provider=Cloudflare', `access_key_id=${accessKey}`, `secret_access_key=${secretKey}`, `endpoint=${endpoint}`, 'acl=private', 'no_check_bucket=true'],
    { stdio: ['inherit', 'ignore', 'inherit'], env },
  );
  if (create.status !== 0) throw new Error(`rclone 設定失敗（結束碼 ${create.status}）`);

  console.log('\n設定存好了，試著寫入再刪掉一個小檔案…');
  const write = spawnSync(rclone, ['rcat', TEST_FILE], { input: 'ok', stdio: ['pipe', 'ignore', 'inherit'], env });
  if (write.status !== 0) throw new Error(`寫不進 ${BUCKET}（結束碼 ${write.status}）。請確認權杖有「物件讀寫」權限，而且範圍包含 ${BUCKET}。`);
  const remove = spawnSync(rclone, ['deletefile', TEST_FILE], { stdio: ['inherit', 'ignore', 'inherit'], env });
  if (remove.status !== 0) throw new Error(`寫入成功，但刪不掉測試檔（結束碼 ${remove.status}）。`);
  console.log(`\n完成：rclone 可以讀寫 ${BUCKET}。`);
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  process.exit(1);
});
