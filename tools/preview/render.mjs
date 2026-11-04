#!/usr/bin/env node
// Render a preview sheet of Bedrock block models to a PNG.
//
//   cd tools/preview && npm install
//   node tools/preview/render.mjs <sheet.json> <out.png>
//
// Paths inside the sheet (geo, texture) are relative to the repository root.
// Uses Playwright's own Chromium if it is installed, otherwise the Chrome or
// Edge already on the computer (the author's Windows, 2026-11-04).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');

const [sheetArg, outArg] = process.argv.slice(2);
if (!sheetArg || !outArg) {
  console.error('usage: node tools/preview/render.mjs <sheet.json> <out.png>');
  process.exit(1);
}
const sheetPath = path.resolve(sheetArg);
const outPath = path.resolve(outArg);

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png' };

const page = `<!doctype html><html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; }
  #sheet { position: relative; font-family: "WenQuanYi Zen Hei", "Noto Sans CJK TC", sans-serif; }
  .title { position: absolute; left: 0; top: 0; width: 100%; height: 48px; line-height: 48px;
           text-align: center; font-size: 22px; color: #222; }
  .label { position: absolute; height: 36px; line-height: 28px; text-align: center; font-size: 17px; color: #333; }
</style>
<script type="importmap">{"imports":{"three":"/tools/preview/node_modules/three/build/three.module.js"}}</script>
</head><body><div id="sheet"></div>
<script type="module">
  import { renderSheet } from '/tools/preview/page.js';
  const sheet = await (await fetch('/__sheet')).json();
  try { window.__done = await renderSheet(sheet); } catch (e) { window.__error = String(e.stack || e); }
</script></body></html>`;

// Serve the repository read-only so the page can fetch models and textures.
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (url === '/') { res.writeHead(200, { 'content-type': TYPES['.html'] }); return res.end(page); }
  if (url === '/__sheet') { res.writeHead(200, { 'content-type': TYPES['.json'] }); return res.end(fs.readFileSync(sheetPath)); }
  const file = path.join(repoRoot, url);
  if (!file.startsWith(repoRoot) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404); return res.end();
  }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const { port } = server.address();

async function launch() {
  const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];
  for (const channel of [undefined, 'chrome']) {
    try { return await chromium.launch({ channel, args }); } catch { /* try the next browser */ }
  }
  return chromium.launch({ channel: 'msedge', args });
}

const browser = await launch();
try {
  const tab = await browser.newPage();
  tab.on('pageerror', (e) => console.error('page error:', e.message));
  await tab.goto(`http://127.0.0.1:${port}/`);
  await tab.waitForFunction(() => window.__done || window.__error, null, { timeout: 60000 });
  const error = await tab.evaluate(() => window.__error);
  if (error) throw new Error(error);
  await tab.locator('#sheet').screenshot({ path: outPath });
  console.log(`wrote ${path.relative(process.cwd(), outPath)}`);
} finally {
  await browser.close();
  server.close();
}
