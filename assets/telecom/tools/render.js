// Render the concept board to PNG and dump each symbol as SVG.
// usage: node render.js <board.html> <out.png> <svg-out-dir>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [html, outPng, svgDir] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(html));
  await page.waitForSelector('body[data-ready="1"]');
  await page.screenshot({ path: outPng, fullPage: true });
  if (svgDir) {
    fs.mkdirSync(svgDir, { recursive: true });
    const symbols = await page.evaluate(() => window.SYMBOLS);
    for (const s of symbols) fs.writeFileSync(path.join(svgDir, `concept-${s.key.toLowerCase()}.svg`), s.svg + '\n');
  }
  await browser.close();
})();
