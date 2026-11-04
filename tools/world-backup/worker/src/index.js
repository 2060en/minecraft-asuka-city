// 雲端地圖的 Cloudflare Worker。
//
//   /            檢視網頁（viewer 資料夾的靜態檔案）
//   /data/...    地圖資料（R2）：index.json、snapshots/*.json、tiles/**
//   /mcp         MCP 伺服器，讓 AI 查詢地圖
//
// 所有請求都要先通過 Cloudflare Access（見 access.js）。

import { verifyAccess } from './access.js';
import { handleMcp } from './mcp.js';

/**
 * @typedef {object} R2ObjectBody
 * @property {ReadableStream} body
 * @property {string} httpEtag
 * @property {(headers: Headers) => void} writeHttpMetadata
 * @property {() => Promise<ArrayBuffer>} arrayBuffer
 * @property {() => Promise<any>} json
 */

/**
 * @typedef {object} Env
 * @property {{ get: (key: string, options?: any) => Promise<R2ObjectBody | (Omit<R2ObjectBody, 'body'> & { body?: undefined }) | null> }} MAP
 * @property {{ fetch: (request: Request) => Promise<Response> }} ASSETS
 * @property {string} [ACCESS_TEAM_DOMAIN]
 * @property {string} [ACCESS_AUD]
 */

/** 只允許這些字元，避免奇怪的路徑 */
const KEY_PATTERN = /^(index\.json|snapshots\/[\w-]+\.json|tiles\/[0-9a-f]{2}\/[0-9a-f]{20}\.[a-z0-9]+)$/;

/**
 * @param {string} key
 */
function cacheControl(key) {
  // 圖磚和每次備份的清單一旦上傳就不會改變；index.json 每次備份都會更新
  return key === 'index.json' ? 'private, no-cache' : 'private, max-age=31536000, immutable';
}

/**
 * @param {Request} request
 * @param {Env} env
 * @param {string} key
 */
async function serveData(request, env, key) {
  if (!KEY_PATTERN.test(key)) return new Response('Not found', { status: 404 });
  const object = await env.MAP.get(key, { onlyIf: request.headers });
  if (!object) return new Response('Not found', { status: 404 });
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('ETag', object.httpEtag);
  headers.set('Cache-Control', cacheControl(key));
  if (!object.body) return new Response(null, { status: 304, headers });
  return new Response(object.body, { headers });
}

/**
 * MCP 工具讀資料用的介面。
 * @param {Env} env
 * @returns {import('./mcp.js').MapStore}
 */
function r2Store(env) {
  return {
    async getJson(key) {
      const object = await env.MAP.get(key);
      return object && object.body ? object.json() : undefined;
    },
    async getBytes(key) {
      const object = await env.MAP.get(key);
      return object && object.body ? new Uint8Array(await object.arrayBuffer()) : undefined;
    },
  };
}

export default {
  /**
   * @param {Request} request
   * @param {Env} env
   */
  async fetch(request, env) {
    const auth = await verifyAccess(request, env);
    if (!auth.ok) return new Response(auth.message, { status: auth.status, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });

    const url = new URL(request.url);
    if (url.pathname === '/mcp') return handleMcp(request, r2Store(env));
    if (url.pathname.startsWith('/data/')) {
      if (request.method !== 'GET' && request.method !== 'HEAD') return new Response('Method not allowed', { status: 405 });
      return serveData(request, env, decodeURIComponent(url.pathname.slice('/data/'.length)));
    }
    return env.ASSETS.fetch(request);
  },
};
