// 一次性設定：讓 Claude Code 透過 MCP 查雲端地圖。雙擊 setup-mcp.bat。
//
// 服務權杖由作者貼進這個視窗，存在 %USERPROFILE%/.config/asuka/map-token.json（不在 repo 裡），
// 再用 claude mcp add 加到使用者層級的設定（%USERPROFILE%/.claude.json，也不在 repo 裡）。
// claude mcp add 可能會把標頭印出來，所以不顯示它的輸出。
// 權杖的密鑰只會顯示一次，所以先存好，連線測試放最後：Access 的政策可以之後再加。

import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { createInterface } from 'node:readline/promises';
import { loadConfig, mapTokenFile } from './lib/config.js';
import { findExe } from './lib/run.js';

const NAME = 'asuka-map';

async function main() {
  const config = loadConfig();
  if (!config.map.url) throw new Error('設定檔還沒有 map.url（地圖網址）。');
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const clientId = (await rl.question('貼上 Client ID 後按 Enter：')).trim();
  const clientSecret = (await rl.question('貼上 Client Secret 後按 Enter：')).trim();
  rl.close();
  if (!clientId.endsWith('.access')) throw new Error('Client ID 應該以 .access 結尾，請確認沒有貼反。沒有更動任何設定。');
  if (!clientSecret) throw new Error('沒有貼上 Client Secret。沒有更動任何設定。');

  const endpoint = `${config.map.url.replace(/\/$/, '')}/mcp`;
  writeFileSync(mapTokenFile, JSON.stringify({ endpoint, clientId, clientSecret }, null, 2));

  const claude = findExe('claude');
  spawnSync(claude, ['mcp', 'remove', '--scope', 'user', NAME], { stdio: 'ignore' });
  const add = spawnSync(
    claude,
    ['mcp', 'add', '--scope', 'user', '--transport', 'http', NAME, endpoint, '--header', `CF-Access-Client-Id: ${clientId}`, '--header', `CF-Access-Client-Secret: ${clientSecret}`],
    { stdio: 'ignore' },
  );
  if (add.error) throw new Error(`找不到 claude：${add.error.message}`);
  if (add.status !== 0) throw new Error(`claude mcp add 失敗（結束碼 ${add.status}）`);
  console.log('\n權杖存好了，Claude Code 也加上了這個 MCP 伺服器。');

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'CF-Access-Client-Id': clientId, 'CF-Access-Client-Secret': clientSecret, 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }),
    redirect: 'manual',
  });
  if (response.ok && (response.headers.get('content-type') ?? '').includes('json')) {
    const { result } = /** @type {any} */ (await response.json());
    console.log(`連線成功，地圖提供的工具：${result.tools.map((/** @type {{ name: string }} */ t) => t.name).join('、')}`);
  } else {
    console.log(`\n還連不上地圖（HTTP ${response.status}）。如果 Access 的政策還沒加這個服務權杖，這是正常的，加好就能連。`);
  }
  console.log('\n完成。可以關掉 Cloudflare 那一頁了。');
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  process.exit(1);
});
