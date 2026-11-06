// 檢查模型網頁的操作都會動：樓層按鈕、游標讀座標、拖曳旋轉、Shift 加標記、參考點漫遊、平面圖模式。
// 改了 viewer.js 或 build.py 之後跑一次。
//
// 用法：node tools/world-model/check_viewer.mjs <網頁.html>
import { launch, open } from './shot.mjs';

const html = process.argv[2];
if (!html) {
  console.error('用法：node check_viewer.mjs <網頁.html>');
  process.exit(2);
}
const browser = await launch();
const problems = [];
const ok = (cond, what) => { console.log(`${cond ? '通過' : '★失敗'}：${what}`); if (!cond) problems.push(what); };
try {
  const { page, errors } = await open(browser, html);
  const status = () => page.evaluate(() => document.getElementById('status').textContent);

  const range = () => page.evaluate(() => [document.getElementById('lo').value, document.getElementById('hi').value].join('～'));
  const floor = page.locator('#floors button').first();
  if (await floor.count()) {
    const was = await range();
    await floor.click();
    const now = await range();
    ok(was !== now, `樓層按鈕改變顯示高度（${was} → ${now}）`);
  }

  await page.click('#vReset');
  await page.mouse.move(800, 480);
  await page.waitForTimeout(200);
  const hover = await status();
  ok(hover.includes('游標指著'), `游標讀座標：${hover.trim()}`);

  const shot = () => page.evaluate(() => document.querySelector('canvas').toDataURL());
  const before = await shot();
  await page.mouse.down(); await page.mouse.move(900, 500, { steps: 8 }); await page.mouse.up();
  await page.waitForTimeout(200);
  ok(before !== await shot(), '拖曳會旋轉畫面');

  await page.keyboard.down('Shift'); await page.mouse.click(780, 470); await page.keyboard.up('Shift');
  const marks = await page.evaluate(() => document.getElementById('marks').textContent);
  ok(marks.startsWith('1.'), `Shift 點一下加標記：${marks}`);

  const point = page.locator('#points button').first();
  if (await point.count()) {
    await point.click();
    await page.waitForTimeout(200);
    ok(await page.evaluate(() => window.MODEL_VIEW.mode) === 'walk', '參考點會切到漫遊');
    const start = await status();
    await page.keyboard.down('w'); await page.waitForTimeout(800); await page.keyboard.up('w');
    ok(start !== await status(), `W 鍵會往前走：${(await status()).split('　')[0]}`);
  }

  await page.click('#vTop');
  await page.waitForTimeout(200);
  ok(await page.evaluate(() => window.MODEL_VIEW.mode) === 'top', '平面圖模式');
  ok(errors.length === 0, `主控台沒有錯誤${errors.length ? '：' + errors.join('；') : ''}`);
} finally {
  await browser.close();
}
process.exitCode = problems.length ? 1 : 0;
