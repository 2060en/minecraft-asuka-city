// 測試 Cloudflare Worker：地圖資料、MCP 工具。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/src/index.js';
import { handleRpc } from '../worker/src/mcp.js';
import { tilesAround, tileBounds, changedAreas } from '../worker/src/mapdata.js';
import { solidPng } from './helpers.js';

// ---------------------------------------------------------------------------
// 假的 R2 與地圖資料
// ---------------------------------------------------------------------------

const PNG_A = solidPng(8, [10, 100, 200]);
const PNG_B = solidPng(8, [200, 50, 50]);
const H_A = 'aa000000000000000000';
const H_B = 'bb000000000000000000';

const manifestOld = {
  version: 1, id: '2026-11-01-2100', createdAt: '2026-11-01T13:00:00.000Z', note: '第一次', restic: 'abc', ext: 'png',
  properties: { worldName: 'Asuka' },
  areas: [{ minX: -256, maxX: 1536, minZ: -256, maxZ: 1536, tiles: 5 }, { minX: -30000000, maxX: -29999744, minZ: 0, maxZ: 256, tiles: 1 }],
  tiles: { 0: { '0,0': H_A, '-1,0': H_A, '0,-1': H_A, '-1,-1': H_A, '5,5': H_A }, '-1': { '0,0': H_A, '-1,-1': H_A } },
};
const manifestNew = {
  ...manifestOld, id: '2026-11-02-0930', createdAt: '2026-11-02T01:30:00.000Z', note: '蓋了機場',
  tiles: { 0: { ...manifestOld.tiles[0], '0,0': H_B, '1,0': H_B, '20,20': H_B }, '-1': manifestOld.tiles['-1'] },
};
const objects = new Map([
  ['index.json', JSON.stringify({ snapshots: [
    { id: manifestNew.id, createdAt: manifestNew.createdAt, note: manifestNew.note, tiles: 8 },
    { id: manifestOld.id, createdAt: manifestOld.createdAt, note: manifestOld.note, tiles: 7 },
  ] })],
  [`snapshots/${manifestOld.id}.json`, JSON.stringify(manifestOld)],
  [`snapshots/${manifestNew.id}.json`, JSON.stringify(manifestNew)],
  [`tiles/aa/${H_A}.png`, PNG_A],
  [`tiles/bb/${H_B}.png`, PNG_B],
]);

/** 模擬 R2 的 get */
const MAP = {
  /** @param {string} key */
  async get(key) {
    if (!objects.has(key)) return null;
    const value = objects.get(key);
    const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : new Uint8Array(value);
    return {
      body: new Blob([bytes]).stream(),
      httpEtag: '"etag"',
      writeHttpMetadata: (/** @type {Headers} */ h) => h.set('Content-Type', key.endsWith('.json') ? 'application/json' : 'image/png'),
      arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
      json: async () => JSON.parse(new TextDecoder().decode(bytes)),
    };
  },
};
const ASSETS = { fetch: async (/** @type {Request} */ r) => new Response(`asset:${new URL(r.url).pathname}`) };
const env = { MAP, ASSETS };
/** @param {string} [path] @param {RequestInit} [init] */
const req = (path = '/', init = {}) => new Request(`https://asuka-map.example.workers.dev${path}`, init);
const store = {
  getJson: async (/** @type {string} */ k) => (objects.has(k) ? JSON.parse(String(objects.get(k))) : undefined),
  getBytes: async (/** @type {string} */ k) => (objects.has(k) ? new Uint8Array(/** @type {Buffer} */ (objects.get(k))) : undefined),
};

test('地圖計算：座標周圍的圖磚、變動區域', () => {
  assert.deepEqual(tilesAround(10, 10, 0).map((t) => [t.x, t.y]), [[-1, -1], [0, -1], [-1, 0], [0, 0]]);
  assert.deepEqual(tilesAround(300, 100, 0).map((t) => [t.x, t.y]), [[0, -1], [1, -1], [0, 0], [1, 0]]);
  assert.deepEqual(tileBounds(-1, 1, 0), { minX: 512, maxX: 1024, minZ: 0, maxZ: 512 });
  const areas = changedAreas(manifestOld, manifestNew, 0);
  assert.deepEqual(areas.map((a) => [a.minX, a.maxX, a.minZ, a.maxZ, a.tiles]), [[0, 512, 0, 256, 2], [5120, 5376, 5120, 5376, 1]]);
});

test('Worker：不用登入就能讀網頁和地圖資料，奇怪的路徑一律 404', async () => {
  assert.equal(await (await worker.fetch(req('/'), env)).text(), 'asset:/');
  const index = await worker.fetch(req('/data/index.json'), env);
  assert.equal(index.status, 200);
  assert.equal(index.headers.get('Cache-Control'), 'private, no-cache');
  const tile = await worker.fetch(req(`/data/tiles/aa/${H_A}.png`), env);
  assert.equal(tile.headers.get('Cache-Control'), 'private, max-age=31536000, immutable');
  assert.deepEqual(new Uint8Array(await tile.arrayBuffer()), new Uint8Array(PNG_A));
  // ../ 會先被網址正規化掉；編碼過的 %2e%2e%2f 解碼後也不符合格式
  for (const bad of ['/data/%2e%2e%2fsecret', '/data/tiles/aa%2f..%2f..%2findex.json', '/data/other.json', '/data/snapshots/x.y.json']) {
    assert.equal((await worker.fetch(req(bad), env)).status, 404, bad);
  }
});

test('Worker：網站只能讀，地圖資料不接受寫入', async () => {
  for (const method of ['PUT', 'POST', 'DELETE']) {
    assert.equal((await worker.fetch(req('/data/index.json', { method, body: method === 'DELETE' ? undefined : 'x' }), env)).status, 405, method);
  }
});

test('MCP：初始化、列出工具', async () => {
  const init = await handleRpc({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '1' } } }, store);
  assert.equal(init.result.protocolVersion, '2025-06-18');
  assert.ok(init.result.capabilities.tools);
  assert.match(init.result.instructions, /X 是東西方向/);
  assert.equal(await handleRpc({ jsonrpc: '2.0', method: 'notifications/initialized' }, store), undefined);
  const list = await handleRpc({ jsonrpc: '2.0', id: 2, method: 'tools/list' }, store);
  assert.deepEqual(list.result.tools.map((t) => t.name), ['list_snapshots', 'get_map_info', 'view_map', 'find_changes']);
  const unknown = await handleRpc({ jsonrpc: '2.0', id: 3, method: 'resources/list' }, store);
  assert.equal(unknown.error.code, -32601);
});

/** @param {string} name @param {object} [args] */
const call = async (name, args = {}) => (await handleRpc({ jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name, arguments: args } }, store)).result;

test('MCP 工具：list_snapshots、get_map_info', async () => {
  const list = await call('list_snapshots');
  assert.match(list.content[0].text, /共 2 次備份/);
  assert.match(list.content[0].text, /2026-11-02-0930（2026-11-02 09:30，台灣時間）：蓋了機場/);
  const info = await call('get_map_info', { snapshot: '2026-11-01-2100' });
  assert.match(info.content[0].text, /世界主體的範圍：X -256～1536，Z -256～1536/);
  assert.match(info.content[0].text, /另外有 1 塊遠處的零星區域.*X -30000000～-29999744/);
  assert.match(info.content[0].text, /0（每張圖磚 256 格）/);
  const missing = await call('get_map_info', { snapshot: 'nope' });
  assert.equal(missing.isError, true);
});

test('MCP 工具：view_map 回傳圖片和座標範圍', async () => {
  const result = await call('view_map', { x: 10, z: 10 });
  const texts = result.content.filter((c) => c.type === 'text').map((c) => c.text);
  const images = result.content.filter((c) => c.type === 'image');
  assert.match(texts[0], /四張圖拼起來涵蓋 X -256～256、Z -256～256/);
  assert.equal(images.length, 4);
  assert.equal(images[3].mimeType, 'image/png');
  assert.deepEqual(new Uint8Array(Buffer.from(images[3].data, 'base64')), new Uint8Array(PNG_B), '右下是新備份改過的圖磚');
  const old = await call('view_map', { x: 10, z: 10, snapshot: '2026-11-01-2100' });
  assert.deepEqual(new Uint8Array(Buffer.from(old.content.filter((c) => c.type === 'image')[3].data, 'base64')), new Uint8Array(PNG_A));
  // 沒有資料的地方、不存在的縮放等級
  const far = await call('view_map', { x: 100000, z: 100000, zoom: 5 });
  assert.match(far.content[0].text, /zoom 0（要求的 5 沒有，改用最接近的）/);
  assert.equal(far.content.filter((c) => c.type === 'image').length, 0);
  assert.match(far.content[1].text, /沒有地圖資料/);
  assert.equal((await call('view_map', { x: 'a', z: 1 })).isError, true);
});

test('MCP 工具：find_changes 找出蓋了哪裡', async () => {
  const result = await call('find_changes');
  assert.match(result.content[0].text, /從 2026-11-01-2100 到 2026-11-02-0930，有 2 個區域有變動/);
  assert.match(result.content[0].text, /1\. X 0～512，Z 0～256，中心 \(256, 128\)，2 張圖磚/);
  const first = await call('find_changes', { to: '2026-11-01-2100' });
  assert.match(first.content[0].text, /是第一次備份/);
});

test('MCP 端點：HTTP 層', async () => {
  const post = (/** @type {unknown} */ body) => worker.fetch(req('/mcp', { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }), env);
  const res = await post({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'list_snapshots', arguments: {} } });
  assert.equal(res.status, 200);
  assert.match((await res.json()).result.content[0].text, /共 2 次備份/);
  assert.equal((await post({ jsonrpc: '2.0', method: 'notifications/initialized' })).status, 202);
  assert.equal((await worker.fetch(req('/mcp'), env)).status, 405);
  assert.equal((await worker.fetch(req('/mcp', { method: 'POST', body: '{' }), env)).status, 400);
});

test('MCP 端點：不接受一次送多個呼叫，一個請求讀的 R2 物件才有上限', async () => {
  const call = { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'view_map', arguments: { x: 0, z: 0 } } };
  const res = await worker.fetch(req('/mcp', { method: 'POST', body: JSON.stringify([call, call]) }), env);
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error.code, -32600);
});
