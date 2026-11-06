// 用無畫面瀏覽器打開模型網頁，照一連串視角截圖（給 plans.py 做平面圖，也可以拿來和遊戲截圖比對）。
//
// 用法：node tools/world-model/shot.mjs <網頁.html> <輸出資料夾> <視角.json>
//
// 視角.json 是一個陣列，每一項：
//   name：檔名（不含 .png）
//   hi、lo：顯示的最高、最低 Y
//   walk：[x, y, z, yaw, pitch] 站在那一格往那個方向看（yaw、pitch 用 Minecraft 的定義）
//   orbit：[方位角, 仰角, 距離, 中心 x, 中心 y, 中心 z]（角度用弧度）
//   top：[中心 x, 中心 z, 每格幾像素] 正上方、北方在上的正投影
//   size：[寬, 高] 畫面大小，預設 1600 × 950
//   panel：false 時隱藏面板、狀態列、指北針
//   glass、people：false 時隱藏玻璃、NPC 與盔甲座
// 瀏覽器用 tools/preview 裝好的 playwright；它自己的瀏覽器沒下載時，改用電腦裡的 Chrome 或 Edge。
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const require = createRequire(new URL('../preview/package.json', import.meta.url));
const { chromium } = require('playwright');

export async function launch() {
  const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
  for (const channel of [undefined, 'chrome', 'msedge']) {
    try { return await chromium.launch({ channel, args }); } catch { /* 換下一個 */ }
  }
  throw new Error('找不到可以用的瀏覽器：請在 tools/preview 執行 npx playwright install chromium，或裝 Chrome');
}

export async function open(browser, html) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(pathToFileURL(path.resolve(html)).href);
  await page.waitForFunction(() => window.MODEL_VIEW || document.getElementById('loading').textContent.includes('失敗'), null, { timeout: 600000 });
  const fail = await page.evaluate(() => document.getElementById('loading').textContent);
  if (fail.includes('失敗')) throw new Error(fail);
  return { page, errors };
}

async function main() {
  const [html, outDir, viewsFile] = process.argv.slice(2);
  if (!viewsFile) {
    console.error('用法：node shot.mjs <網頁.html> <輸出資料夾> <視角.json>');
    process.exit(2);
  }
  const views = JSON.parse(fs.readFileSync(viewsFile, 'utf8'));
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await launch();
  try {
    const { page, errors } = await open(browser, html);
    for (const v of views) {
      if (v.size) { await page.setViewportSize({ width: v.size[0], height: v.size[1] }); await page.waitForTimeout(300); }
      await page.evaluate((v) => {
        const V = window.MODEL_VIEW;
        const check = (id, on) => { const c = document.getElementById(id); c.checked = on; c.onchange({ target: c }); };
        if (v.hi !== undefined) { V.hi.value = v.hi; V.lo.value = v.lo ?? V.lo.min; V.applyRange(); }
        if (v.glass !== undefined) check('showGlass', v.glass);
        if (v.people !== undefined) check('showPeople', v.people);
        if (v.panel === false) for (const id of ['panel', 'hide', 'status', 'compass']) document.getElementById(id).style.display = 'none';
        if (v.walk) V.goWalk(...v.walk);
        if (v.orbit) V.orbit(...v.orbit);
        if (v.top) V.top(...v.top);
        V.render();
      }, v);
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(outDir, v.name + '.png') });
      console.log('截圖', v.name);
    }
    if (errors.length) { console.error('網頁錯誤：', errors); process.exitCode = 1; }
  } finally {
    await browser.close();
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) await main();
