// 測試圖磚處理與上傳流程：npm test（在 tools/world-backup 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, readdirSync, existsSync, cpSync, writeFileSync, utimesSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { delimiter, join } from 'node:path';
import { parseTilePath, parseMapProperties, buildManifest, mapAreas, snapshotId, tileObjectKey } from '../lib/tiles.js';
import { publishMap } from '../lib/publish.js';
import { installBlockStyles, mapSettingsFile, parseR2Endpoint, unminedRenderArgs } from '../lib/config.js';
import { reportRow, formatBytes } from '../lib/report.js';
import { expandEnv, findExe } from '../lib/run.js';
import { solidPng, writeTile, writeProperties } from './helpers.js';

test('解析 uNmINeD 的圖磚路徑', () => {
  assert.deepEqual(parseTilePath('tiles/zoom.0/1/-1/tile.12.-3.png'), { zoom: 0, x: 12, y: -3, ext: 'png' });
  assert.deepEqual(parseTilePath('tiles/zoom.-2/-1/0/tile.-1.5.jpeg'), { zoom: -2, x: -1, y: 5, ext: 'jpeg' });
  assert.equal(parseTilePath('tiles/zoom.0/0/0/tile.12.3.png'), undefined, '資料夾編號對不上');
  assert.equal(parseTilePath('unmined.js'), undefined);
});

test('讀出 unmined.map.properties.js', () => {
  const source = `var UnminedMapProperties = {
    minZoom: -6,
    maxZoom: 3,
    imageFormat: "jpeg",
    worldName: "My \\"World\\"",
    markers: [],
    enableGrid: true,
    centerX: -120.5
}`;
  assert.deepEqual(parseMapProperties(source), { minZoom: -6, maxZoom: 3, imageFormat: 'jpeg', worldName: 'My "World"', enableGrid: true, centerX: -120.5 });
});

test('組出地圖清單：依縮放等級分組，只保留檢視網頁用得到的設定', () => {
  const manifest = buildManifest({
    id: 'a', createdAt: 't', note: '', restic: '',
    properties: { minZoom: -1, maxZoom: 0, imageFormat: 'png', enableGrid: true },
    tiles: [
      { tile: { zoom: 0, x: 1, y: 2, ext: 'png' }, hash: 'h1' },
      { tile: { zoom: -1, x: 0, y: 1, ext: 'png' }, hash: 'h2' },
    ],
  });
  assert.deepEqual(manifest.tiles, { 0: { '1,2': 'h1' }, '-1': { '0,1': 'h2' } });
  assert.deepEqual(manifest.properties, { minZoom: -1, maxZoom: 0, imageFormat: 'png' });
  assert.equal(manifest.ext, 'png');
  assert.throws(() => buildManifest({ id: 'a', createdAt: 't', note: '', restic: '', properties: {}, tiles: [
    { tile: { zoom: 0, x: 0, y: 0, ext: 'png' }, hash: 'a' },
    { tile: { zoom: 0, x: 1, y: 0, ext: 'jpeg' }, hash: 'b' },
  ] }), /好幾種格式/);
});

test('uNmINeD 真實輸出的路徑：負座標的資料夾、自己的中繼資料不算圖磚', () => {
  // 路徑取自 2026-11-05 實際渲染作者世界的結果
  assert.deepEqual(parseTilePath('tiles/zoom.0/-1/-1/tile.-1.-10.png'), { zoom: 0, x: -1, y: -10, ext: 'png' });
  assert.deepEqual(parseTilePath('tiles/zoom.0/-11719/11718/tile.-117187.117186.webp'), { zoom: 0, x: -117187, y: 117186, ext: 'webp' });
  assert.equal(parseTilePath('tiles/zoom.-1/metadata/k.-1.-1.csv'), undefined);
});

test('地圖分區：遠處的零星區塊自成一塊，不會把主體的範圍撐大', () => {
  /** @param {number} x @param {number} y @param {number} [zoom] */
  const at = (x, y, zoom = 0) => ({ tile: { zoom, x, y, ext: 'webp' } });
  const tiles = [
    at(0, 0), at(1, 0), at(0, 1),
    at(20, 0), // 相距約 5000 格，隔一格（4096 格）以內併在一起
    at(-117187, 117186), at(-117186, 117186), // 世界邊界
    at(-1, -1, -1), // zoom -1 不重複計算
  ];
  assert.deepEqual(mapAreas(tiles), [
    { minX: 0, maxX: 5376, minZ: 0, maxZ: 512, tiles: 4 },
    { minX: -29999872, maxX: -29999360, minZ: 29999616, maxZ: 29999872, tiles: 2 },
  ]);
  assert.deepEqual(mapAreas([]), []);
  // 沒有 zoom 0 時用最接近的等級
  assert.deepEqual(mapAreas([at(1, 1, -2)]), [{ minX: 1024, maxX: 2048, minZ: 1024, maxZ: 2048, tiles: 1 }]);
});

test('uNmINeD 的參數：一律全部重畫、預設用 WebP、套用固定的外觀、不印每張圖磚，設定檔可以改', () => {
  const base = { worldPath: 'C:/world/PXjOwjIpBg0=', map: { renderDir: 'C:/render', stateDir: 'C:/state' } };
  assert.deepEqual(unminedRenderArgs({ ...base, unmined: { exe: 'u', extraArgs: [] } }), [
    'web', 'render', '--world=C:/world/PXjOwjIpBg0=', '--output=C:/render', '--force', '--imageformat=webp', `--mapsettings=${mapSettingsFile}`, '--shadows=3d', '--log-level=warning',
  ]);
  assert.deepEqual(unminedRenderArgs({ ...base, unmined: { exe: 'u', extraArgs: ['--imageformat=png', '--shadows=2d'] } }).slice(5), [
    `--mapsettings=${mapSettingsFile}`, '--log-level=warning', '--imageformat=png', '--shadows=2d',
  ]);
});

test('地圖外觀：水和草不隨生態域變色，草色複製到 uNmINeD 讀得到的地方', () => {
  const { Settings } = JSON.parse(readFileSync(mapSettingsFile, 'utf8')).StylesheetSettings;
  assert.equal(Settings.biomeTintsWater, 'False');
  assert.equal(Settings.biomeTintsGrass, 'False');
  assert.equal(Settings.biomeColoring, 'False');

  const dir = mkdtempSync(join(tmpdir(), 'unmined-'));
  mkdirSync(join(dir, 'config'));
  writeFileSync(join(dir, 'config', 'custom.blockstyles.txt'), '舊內容');
  installBlockStyles(join(dir, 'unmined-cli.exe'));
  assert.match(readFileSync(join(dir, 'config', 'custom.blockstyles.txt'), 'utf8'), /^#grassblock, #grass = #[0-9a-f]{6}$/m);
});

test('從 Cloudflare 顯示的網址取出 R2 端點', () => {
  const id = 'b54f07a6c269ecca2fa60f1ae4920c99';
  assert.equal(parseR2Endpoint(` https://${id}.r2.cloudflarestorage.com/asuka-map \n`), `https://${id}.r2.cloudflarestorage.com`);
  assert.equal(parseR2Endpoint(`https://${id}.eu.r2.cloudflarestorage.com`), `https://${id}.eu.r2.cloudflarestorage.com`);
  assert.equal(parseR2Endpoint('https://example.com'), undefined);
  assert.equal(parseR2Endpoint(id), undefined);
});

test('備份編號依時間產生，重複時加上序號', () => {
  const d = new Date(2026, 10, 1, 21, 5);
  assert.equal(snapshotId(d, new Set()), '2026-11-01-2105');
  assert.equal(snapshotId(d, new Set(['2026-11-01-2105'])), '2026-11-01-2105-2');
  assert.equal(snapshotId(d, new Set(['2026-11-01-2105', '2026-11-01-2105-2'])), '2026-11-01-2105-3');
});

test('雲端的圖磚路徑', () => {
  assert.equal(tileObjectKey('abcdef0123456789abcd', 'png'), 'tiles/ab/abcdef0123456789abcd.png');
});

/** 模擬 rclone：把 staging 的內容複製到「雲端」資料夾 */
function fakeRemote() {
  const remote = mkdtempSync(join(tmpdir(), 'remote-'));
  const calls = [];
  return {
    remote,
    calls,
    upload: async (/** @type {string} */ staging, /** @type {number} */ n) => {
      calls.push(n);
      cpSync(staging, remote, { recursive: true });
    },
  };
}

/** @param {string} dir */
function listFiles(dir, prefix = '') {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? listFiles(join(dir, e.name), `${prefix}${e.name}/`) : [`${prefix}${e.name}`],
  );
}

test('上傳流程：第一次全部上傳，第二次只傳有變動的圖磚，相同內容只存一份', async () => {
  const render = mkdtempSync(join(tmpdir(), 'render-'));
  const state = mkdtempSync(join(tmpdir(), 'state-'));
  const { remote, calls, upload } = fakeRemote();
  writeProperties(render);
  const blue = solidPng(16, [40, 90, 200]);
  const green = solidPng(16, [40, 160, 60]);
  writeTile(render, 0, 0, 0, blue);
  writeTile(render, 0, -1, 0, blue); // 內容和上一張一樣（例如兩片海）
  writeTile(render, 0, 0, -1, green);
  writeTile(render, -1, -1, -1, green);

  const first = await publishMap({ renderDir: render, stateDir: state, note: '第一次', restic: 'abc12345', now: new Date(2026, 10, 1, 21, 0), upload });
  assert.equal(first.id, '2026-11-01-2100');
  assert.equal(first.tiles, 4);
  assert.equal(first.newTiles, 2, '只有兩種內容');
  assert.equal(listFiles(join(remote, 'tiles')).length, 2);
  const m1 = JSON.parse(readFileSync(join(remote, 'snapshots', `${first.id}.json`), 'utf8'));
  assert.equal(m1.note, '第一次');
  assert.equal(m1.restic, 'abc12345');
  assert.equal(m1.tiles[0]['0,0'], m1.tiles[0]['-1,0']);
  assert.equal(m1.properties.worldName, 'Asuka World');
  assert.ok(!existsSync(join(state, 'staging')), '上傳完清掉 staging');

  // 第二次：一張圖磚改了，一張新增
  const red = solidPng(16, [200, 40, 40]);
  writeTile(render, 0, 0, 0, red);
  writeTile(render, 0, 1, 0, green);
  const second = await publishMap({ renderDir: render, stateDir: state, note: '', restic: 'def67890', now: new Date(2026, 10, 2, 9, 30), upload });
  assert.equal(second.tiles, 5);
  assert.equal(second.newTiles, 1, '只有紅色是新的內容');
  assert.deepEqual(calls, [2, 1]);
  const index = JSON.parse(readFileSync(join(remote, 'index.json'), 'utf8'));
  assert.deepEqual(index.snapshots.map((s) => s.id), ['2026-11-02-0930', '2026-11-01-2100']);
  const m2 = JSON.parse(readFileSync(join(remote, 'snapshots', `${second.id}.json`), 'utf8'));
  assert.notEqual(m2.tiles[0]['0,0'], m1.tiles[0]['0,0']);
  assert.equal(m2.tiles[0]['0,-1'], m1.tiles[0]['0,-1']);
  // 舊的清單還在，可以切回去看
  assert.ok(existsSync(join(remote, 'snapshots', `${first.id}.json`)));
});

test('上傳失敗時不更新本機狀態，重跑會再傳一次', async () => {
  const render = mkdtempSync(join(tmpdir(), 'render-'));
  const state = mkdtempSync(join(tmpdir(), 'state-'));
  writeProperties(render);
  writeTile(render, 0, 0, 0, solidPng(8, [1, 2, 3]));
  await assert.rejects(
    publishMap({ renderDir: render, stateDir: state, note: '', restic: '', upload: async () => { throw new Error('網路斷了'); } }),
    /網路斷了/,
  );
  const { calls, upload } = fakeRemote();
  const summary = await publishMap({ renderDir: render, stateDir: state, note: '', restic: '', upload });
  assert.equal(summary.newTiles, 1);
  assert.deepEqual(calls, [1]);
});

test('沒變的圖磚不重算雜湊值；內容變了才重算', async () => {
  const render = mkdtempSync(join(tmpdir(), 'render-'));
  const state = mkdtempSync(join(tmpdir(), 'state-'));
  const { upload } = fakeRemote();
  writeProperties(render);
  writeTile(render, 0, 0, 0, solidPng(8, [9, 9, 9]));
  await publishMap({ renderDir: render, stateDir: state, note: '', restic: '', now: new Date(2026, 0, 1), upload });
  const cache = JSON.parse(readFileSync(join(state, 'tilecache.json'), 'utf8'));
  const key = 'tiles/zoom.0/0/0/tile.0.0.png';
  // 偷改快取裡的雜湊值：大小和時間沒變，就應該沿用（證明沒有重算）
  cache[key][2] = 'ffffffffffffffffffff';
  writeFileSync(join(state, 'tilecache.json'), JSON.stringify(cache));
  const second = await publishMap({ renderDir: render, stateDir: state, note: '', restic: '', now: new Date(2026, 0, 2), upload });
  assert.equal(second.newTiles, 1);
  // 改了檔案時間就會重算
  const file = join(render, key);
  utimesSync(file, new Date(), new Date(Date.now() + 5000));
  const third = await publishMap({ renderDir: render, stateDir: state, note: '', restic: '', now: new Date(2026, 0, 3), upload });
  assert.equal(third.newTiles, 0, '重算後是第一次就上傳過的雜湊值');
});

test('沒有渲染結果時給出清楚的錯誤', async () => {
  const render = mkdtempSync(join(tmpdir(), 'render-'));
  const state = mkdtempSync(join(tmpdir(), 'state-'));
  await assert.rejects(publishMap({ renderDir: render, stateDir: state, note: '', restic: '', upload: async () => {} }), /還沒渲染/);
});

test('備份紀錄的表格列', () => {
  const row = reportRow({
    date: new Date(2026, 10, 1, 21, 5),
    note: '蓋好 | 第二航廈',
    backup: { snapshot: 'abc12345', worldBytes: 1.9 * 1024 ** 3, addedBytes: 12 * 1024 ** 2 },
    map: { id: '2026-11-01-2105', tiles: 1200, newTiles: 35 },
  });
  assert.equal(row, '| 2026-11-01 21:05 | 蓋好 \\| 第二航廈 | `abc12345` | 1.9 GB | 12.0 MB | `2026-11-01-2105` | 1200（35） |\n');
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(512), '512 B');
});

test('展開 Windows 環境變數', () => {
  assert.equal(expandEnv('%APPDATA%/Minecraft Bedrock', { AppData: 'C:/Users/ian/AppData/Roaming' }), 'C:/Users/ian/AppData/Roaming/Minecraft Bedrock');
  assert.equal(expandEnv('%NOPE%/x', {}), '%NOPE%/x');
});

test('找外部程式：給路徑就照用，先找 PATH，再找 winget 的安裝資料夾', () => {
  const root = mkdtempSync(join(tmpdir(), 'exe-'));
  const touch = (/** @type {string[]} */ ...parts) => {
    const file = join(root, ...parts);
    mkdirSync(join(file, '..'), { recursive: true });
    writeFileSync(file, '');
    return file;
  };
  const packages = ['local', 'Microsoft', 'WinGet', 'Packages'];
  const restic = touch(...packages, 'restic.restic_Microsoft.Winget.Source_8wekyb3d8bbwe', 'restic_0.19.1_windows_amd64.exe');
  const rclone = touch(...packages, 'Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe', 'rclone-v1.75.2-windows-amd64', 'rclone.exe');
  touch(...packages, 'Rclone.Rclone_Microsoft.Winget.Source_8wekyb3d8bbwe', 'rclone-v1.75.2-windows-amd64', 'git-rclone-helper.exe');
  touch(...packages, 'resticprofile.resticprofile_x', 'resticprofile.exe');
  const onPath = touch('bin', 'restic.exe');
  const winget = { LOCALAPPDATA: join(root, 'local'), PATH: '' };

  assert.equal(findExe('C:/tools/restic.exe', winget), 'C:/tools/restic.exe', '給完整路徑就照用');
  assert.equal(findExe('restic', winget), restic, 'PATH 沒有時找 winget 的資料夾，檔名可以帶版本號');
  assert.equal(findExe('rclone', winget), rclone, '要找得到子資料夾裡的程式');
  assert.equal(findExe('restic', { ...winget, PATH: ['nope', join(root, 'bin')].join(delimiter) }), onPath, 'PATH 優先');
  assert.equal(findExe('unmined-cli', winget), 'unmined-cli', '哪裡都找不到就原樣回傳，讓執行時報錯');
  assert.equal(findExe('restic', {}), 'restic', '沒有環境變數也不會壞');
});
