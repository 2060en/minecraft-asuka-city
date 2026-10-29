const { chromium } = require('playwright');
// usage: node shot.js out.png "view=side&w=2400&h=1000"
(async()=>{
  const [out, q] = process.argv.slice(2);
  const qs = new URLSearchParams(q); const w=+qs.get('w')||2400, h=+qs.get('h')||1000;
  const b = await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const p = await b.newPage({viewport:{width:w,height:h}});
  p.on('console', m => { if (m.type()==='error' || m.type()==='warning') console.log('[page]', m.text().slice(0,400)); });
  p.on('pageerror', e => console.log('[pageerror]', e.message));
  const t0=Date.now();
  await p.goto('http://127.0.0.1:8765/index.html?'+q);
  await p.waitForFunction('window.__done===true', null, {timeout: 600000});
  await p.screenshot({path: out});
  console.log('rendered', out, ((Date.now()-t0)/1000).toFixed(1)+'s');
  await b.close();
})();
