// 一次性設定：讓 Claude Code 透過 MCP 查雲端地圖。雙擊 setup-mcp.bat。
//
// 地圖是公開的，不需要權杖。用 claude mcp add 加到使用者層級的設定（%USERPROFILE%/.claude.json）。

import { spawnSync } from 'node:child_process';
import { loadConfig } from './lib/config.js';
import { findExe } from './lib/run.js';

const NAME = 'asuka-map';

async function main() {
  const config = loadConfig();
  if (!config.map.url) throw new Error('設定檔還沒有 map.url（地圖網址）。');
  const endpoint = `${config.map.url.replace(/\/$/, '')}/mcp`;

  const claude = findExe('claude');
  spawnSync(claude, ['mcp', 'remove', '--scope', 'user', NAME], { stdio: 'ignore' });
  const add = spawnSync(claude, ['mcp', 'add', '--scope', 'user', '--transport', 'http', NAME, endpoint], { stdio: 'ignore' });
  if (add.error) throw new Error(`找不到 claude：${add.error.message}`);
  if (add.status !== 0) throw new Error(`claude mcp add 失敗（結束碼 ${add.status}）`);
  console.log('Claude Code 加上了這個 MCP 伺服器。');

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/list' }),
    redirect: 'manual',
  });
  if (response.ok && (response.headers.get('content-type') ?? '').includes('json')) {
    const { result } = /** @type {any} */ (await response.json());
    console.log(`連線成功，地圖提供的工具：${result.tools.map((/** @type {{ name: string }} */ t) => t.name).join('、')}`);
  } else {
    console.log(`\n連不上地圖（HTTP ${response.status}）。`);
  }
}

main().catch((error) => {
  console.error(`\n失敗：${error instanceof Error ? error.message : error}`);
  process.exit(1);
});
