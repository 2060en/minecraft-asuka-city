// MCP 伺服器：讓 AI（例如 Claude Code）查詢雲端地圖。
//
// 用 MCP 的 Streamable HTTP 傳輸，無狀態：每個 POST 是一則 JSON-RPC 訊息，直接回 JSON。
// 目前的工具都是用渲染好的圖磚：列出備份、看某個座標周圍的俯視圖、找出兩次備份之間有變動的區域。
// 「某個座標是什麼方塊」需要另外匯出方塊資料，見 tools/world-backup/README.md 的「第二階段」。

import { blocksPerTile, tileBounds, tilesAround, zoomLevels, changedAreas } from './mapdata.js';

/** @typedef {import('./mapdata.js').Manifest} Manifest */

/**
 * 讀取地圖資料的介面（正式環境是 R2，測試時用假的）。
 * @typedef {object} MapStore
 * @property {(key: string) => Promise<any | undefined>} getJson
 * @property {(key: string) => Promise<Uint8Array | undefined>} getBytes
 */

const SUPPORTED_VERSIONS = ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05'];

const INSTRUCTIONS = `這是作者在 Minecraft 基岩版建造的架空島國「津蘭賀千良」（首都 Asuka City）的雲端地圖，資料來自每次備份時用 uNmINeD 渲染的俯視圖。
座標：X 是東西方向（往東增加），Z 是南北方向（往南增加），俯視圖北方在上。
縮放：zoom 0 是 1 格 1 像素，每張圖磚 256 × 256 像素；zoom -1 是 2 格 1 像素，zoom 1 是 1 格 2 像素。
用法：先用 list_snapshots 看有哪些備份，用 view_map 看某個座標周圍的樣子，用 find_changes 找出兩次備份之間蓋了哪裡。`;

const TOOLS = [
  {
    name: 'list_snapshots',
    description: '列出所有備份的地圖（新的在前面），包含備份編號、時間、作者寫的備註、圖磚數。',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'get_map_info',
    description: '取得一次備份的地圖資訊：世界名稱、世界主體的座標範圍、遠處的零星區域、可用的縮放等級。',
    inputSchema: {
      type: 'object',
      properties: { snapshot: { type: 'string', description: '備份編號；省略時用最新的備份' } },
      additionalProperties: false,
    },
  },
  {
    name: 'view_map',
    description:
      '看某個座標周圍的俯視圖。回傳 2 × 2 張圖磚的圖片，座標落在四張圖中間附近，每張圖都附上涵蓋的座標範圍。zoom 越大越清楚、範圍越小：zoom 0 四張圖共涵蓋 512 × 512 格，zoom 1 涵蓋 256 × 256 格，zoom -2 涵蓋 2048 × 2048 格。',
    inputSchema: {
      type: 'object',
      properties: {
        x: { type: 'number', description: 'X 座標（東西方向）' },
        z: { type: 'number', description: 'Z 座標（南北方向）' },
        zoom: { type: 'integer', description: '縮放等級，預設 0（1 格 1 像素）' },
        snapshot: { type: 'string', description: '備份編號；省略時用最新的備份' },
      },
      required: ['x', 'z'],
      additionalProperties: false,
    },
  },
  {
    name: 'find_changes',
    description:
      '比較兩次備份，找出地圖有變動的區域（例如新蓋的建築、道路），依變動大小排序。每個區域附上座標範圍與中心點，可以再用 view_map 看細節。',
    inputSchema: {
      type: 'object',
      properties: {
        from: { type: 'string', description: '較舊的備份編號；省略時用 to 的前一次備份' },
        to: { type: 'string', description: '較新的備份編號；省略時用最新的備份' },
        limit: { type: 'integer', description: '最多回傳幾個區域，預設 20' },
      },
      additionalProperties: false,
    },
  },
];

class ToolError extends Error {}

/**
 * @param {Uint8Array} bytes
 */
function toBase64(bytes) {
  let binary = '';
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

/**
 * @param {string} ext
 */
function mimeType(ext) {
  if (ext === 'jpg' || ext === 'jpeg') return 'image/jpeg';
  if (ext === 'webp') return 'image/webp';
  return 'image/png';
}

/**
 * @param {MapStore} store
 * @returns {Promise<{ id: string, createdAt: string, note: string, tiles: number }[]>}
 */
async function listSnapshots(store) {
  const index = await store.getJson('index.json');
  return index?.snapshots ?? [];
}

/**
 * @param {MapStore} store
 * @param {string | undefined} id
 * @returns {Promise<Manifest>}
 */
async function loadManifest(store, id) {
  const snapshots = await listSnapshots(store);
  if (snapshots.length === 0) throw new ToolError('雲端還沒有任何備份的地圖。');
  const target = id ?? snapshots[0].id;
  if (!/^[\w-]+$/.test(target)) throw new ToolError(`備份編號格式不對：${target}`);
  const manifest = await store.getJson(`snapshots/${target}.json`);
  if (!manifest) throw new ToolError(`找不到備份 ${target}，可以用 list_snapshots 查看有哪些備份。`);
  return manifest;
}

/**
 * @param {string} createdAt
 */
function localTime(createdAt) {
  // 作者在台灣，用 UTC+8 顯示
  return new Date(new Date(createdAt).getTime() + 8 * 3600 * 1000).toISOString().replace('T', ' ').slice(0, 16);
}

/**
 * @param {MapStore} store
 * @param {string} name
 * @param {any} args
 * @returns {Promise<any[]>} MCP 的 content 陣列
 */
async function callTool(store, name, args) {
  if (name === 'list_snapshots') {
    const snapshots = await listSnapshots(store);
    if (snapshots.length === 0) return [{ type: 'text', text: '雲端還沒有任何備份的地圖。' }];
    const lines = snapshots.map((s) => `・${s.id}（${localTime(s.createdAt)}，台灣時間）${s.note ? `：${s.note}` : ''}，${s.tiles} 張圖磚`);
    return [{ type: 'text', text: `共 ${snapshots.length} 次備份，新的在前面：\n${lines.join('\n')}` }];
  }

  if (name === 'get_map_info') {
    const manifest = await loadManifest(store, args.snapshot);
    const levels = zoomLevels(manifest);
    const p = manifest.properties;
    const [main, ...others] = manifest.areas ?? [];
    const range = (/** @type {{ minX: number, maxX: number, minZ: number, maxZ: number }} */ a) => `X ${a.minX}～${a.maxX}，Z ${a.minZ}～${a.maxZ}`;
    const text = [
      `備份：${manifest.id}（${localTime(manifest.createdAt)}，台灣時間）${manifest.note ? `，備註：${manifest.note}` : ''}`,
      `世界名稱：${p.worldName ?? '（未知）'}`,
      main ? `世界主體的範圍：${range(main)}` : '世界主體的範圍：（沒有圖磚）',
      ...(others.length > 0 ? [`另外有 ${others.length} 塊遠處的零星區域（飛過或傳送時留下的）：${others.map((a) => `${range(a)}（${a.tiles} 張圖磚）`).join('；')}`] : []),
      `可用的縮放等級：${levels.map((z) => `${z}（每張圖磚 ${blocksPerTile(z)} 格）`).join('、')}`,
      `圖磚格式：${manifest.ext}`,
    ].join('\n');
    return [{ type: 'text', text }];
  }

  if (name === 'view_map') {
    const x = Number(args.x);
    const z = Number(args.z);
    if (!Number.isFinite(x) || !Number.isFinite(z)) throw new ToolError('x、z 要是數字。');
    const manifest = await loadManifest(store, args.snapshot);
    const levels = zoomLevels(manifest);
    if (levels.length === 0) throw new ToolError('這次備份沒有圖磚。');
    const wanted = Number.isInteger(args.zoom) ? args.zoom : 0;
    const zoom = Math.min(levels[levels.length - 1], Math.max(levels[0], wanted));
    const tiles = manifest.tiles[zoom] ?? {};
    const parts = tilesAround(x, z, zoom);
    const first = tileBounds(zoom, parts[0].x, parts[0].y);
    const last = tileBounds(zoom, parts[3].x, parts[3].y);
    /** @type {any[]} */
    const content = [
      {
        type: 'text',
        text:
          `備份 ${manifest.id}，座標 (${x}, ${z}) 周圍的俯視圖，zoom ${zoom}${zoom !== wanted ? `（要求的 ${wanted} 沒有，改用最接近的）` : ''}，` +
          `每張圖 256 × 256 像素、涵蓋 ${blocksPerTile(zoom)} × ${blocksPerTile(zoom)} 格。` +
          `四張圖拼起來涵蓋 X ${first.minX}～${last.maxX}、Z ${first.minZ}～${last.maxZ}，北方在上。`,
      },
    ];
    for (const part of parts) {
      const b = tileBounds(zoom, part.x, part.y);
      const label = `${part.position}：X ${b.minX}～${b.maxX}，Z ${b.minZ}～${b.maxZ}`;
      const hash = tiles[`${part.x},${part.y}`];
      const bytes = hash ? await store.getBytes(`tiles/${hash.slice(0, 2)}/${hash}.${manifest.ext}`) : undefined;
      if (!bytes) {
        content.push({ type: 'text', text: `${label}（這裡沒有地圖資料，可能是還沒探索過的區域）` });
        continue;
      }
      content.push({ type: 'text', text: label });
      content.push({ type: 'image', data: toBase64(bytes), mimeType: mimeType(manifest.ext) });
    }
    return content;
  }

  if (name === 'find_changes') {
    const snapshots = await listSnapshots(store);
    if (snapshots.length === 0) throw new ToolError('雲端還沒有任何備份的地圖。');
    const toId = args.to ?? snapshots[0].id;
    const toIndex = snapshots.findIndex((s) => s.id === toId);
    if (toIndex < 0) throw new ToolError(`找不到備份 ${toId}。`);
    const fromId = args.from ?? snapshots[toIndex + 1]?.id;
    const after = await loadManifest(store, toId);
    const before = fromId ? await loadManifest(store, fromId) : undefined;
    const levels = zoomLevels(after);
    const zoom = levels.includes(0) ? 0 : levels.reduce((best, z) => (Math.abs(z) < Math.abs(best) ? z : best), levels[0]);
    const areas = changedAreas(before, after, zoom);
    const limit = Number.isInteger(args.limit) && args.limit > 0 ? args.limit : 20;
    const header = before
      ? `從 ${before.id} 到 ${after.id}，有 ${areas.length} 個區域有變動（以每 ${blocksPerTile(zoom)} 格一張的圖磚比較）`
      : `${after.id} 是第一次備份，沒有可以比較的對象；以下是所有有地圖的區域`;
    if (areas.length === 0) return [{ type: 'text', text: `${header}。` }];
    const lines = areas
      .slice(0, limit)
      .map((a, i) => `${i + 1}. X ${a.minX}～${a.maxX}，Z ${a.minZ}～${a.maxZ}，中心 (${a.centerX}, ${a.centerZ})，${a.tiles} 張圖磚`);
    const more = areas.length > limit ? `\n（還有 ${areas.length - limit} 個較小的區域沒列出）` : '';
    return [{ type: 'text', text: `${header}：\n${lines.join('\n')}${more}` }];
  }

  throw new ToolError(`沒有這個工具：${name}`);
}

/**
 * 處理一則 JSON-RPC 訊息；通知（沒有 id）回傳 undefined。
 * @param {any} message
 * @param {MapStore} store
 */
export async function handleRpc(message, store) {
  const { id, method, params } = message ?? {};
  const isRequest = id !== undefined && id !== null;
  /** @param {number} code @param {string} text */
  const error = (code, text) => ({ jsonrpc: '2.0', id: isRequest ? id : null, error: { code, message: text } });

  if (!isRequest) return undefined; // 通知（例如 notifications/initialized）和回應都不用回
  if (typeof method !== 'string') return error(-32600, 'Invalid Request');

  switch (method) {
    case 'initialize': {
      const requested = params?.protocolVersion;
      return {
        jsonrpc: '2.0',
        id,
        result: {
          protocolVersion: SUPPORTED_VERSIONS.includes(requested) ? requested : SUPPORTED_VERSIONS[0],
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'asuka-map', version: '1.0.0' },
          instructions: INSTRUCTIONS,
        },
      };
    }
    case 'ping':
      return { jsonrpc: '2.0', id, result: {} };
    case 'tools/list':
      return { jsonrpc: '2.0', id, result: { tools: TOOLS } };
    case 'tools/call': {
      const name = params?.name;
      if (!TOOLS.some((t) => t.name === name)) return error(-32602, `Unknown tool: ${name}`);
      try {
        const content = await callTool(store, name, params?.arguments ?? {});
        return { jsonrpc: '2.0', id, result: { content } };
      } catch (e) {
        if (e instanceof ToolError) return { jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: e.message }], isError: true } };
        return error(-32603, `Internal error: ${e instanceof Error ? e.message : e}`);
      }
    }
    default:
      return error(-32601, `Method not found: ${method}`);
  }
}

/**
 * 處理 /mcp 的 HTTP 請求。
 * @param {Request} request
 * @param {MapStore} store
 */
export async function handleMcp(request, store) {
  if (request.method !== 'POST') {
    return new Response('這個 MCP 伺服器只接受 POST（無狀態的 Streamable HTTP）。', { status: 405, headers: { Allow: 'POST' } });
  }
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }, { status: 400 });
  }
  const messages = Array.isArray(body) ? body : [body];
  const responses = (await Promise.all(messages.map((m) => handleRpc(m, store)))).filter((r) => r !== undefined);
  if (responses.length === 0) return new Response(null, { status: 202 });
  return Response.json(Array.isArray(body) ? responses : responses[0]);
}
