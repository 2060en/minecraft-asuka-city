// 確認請求有通過 Cloudflare Access 的登入。
//
// Cloudflare Access 擋在 Worker 前面：瀏覽器用 email 驗證碼登入，AI 工具用服務權杖（service token）。
// 通過的請求會帶著 Access 簽發的 JWT（Cf-Access-Jwt-Assertion 標頭）。
// 這裡再驗一次簽章，就算 Access 不小心被關掉，地圖也不會變成公開的。

/** @type {{ team: string, keys: JsonWebKey[], fetchedAt: number } | undefined} */
let keyCache;

/**
 * @param {string} text
 */
function base64UrlToBytes(text) {
  const base64 = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4);
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/**
 * @param {string} text
 */
function decodeJson(text) {
  return JSON.parse(new TextDecoder().decode(base64UrlToBytes(text)));
}

/**
 * @param {string} team 例如 asuka.cloudflareaccess.com
 * @param {typeof fetch} fetcher
 */
async function getKeys(team, fetcher) {
  if (keyCache && keyCache.team === team && Date.now() - keyCache.fetchedAt < 60 * 60 * 1000) return keyCache.keys;
  const response = await fetcher(`https://${team}/cdn-cgi/access/certs`);
  if (!response.ok) throw new Error(`讀不到 Access 的公鑰（${response.status}）`);
  const { keys } = /** @type {{ keys: JsonWebKey[] }} */ (await response.json());
  keyCache = { team, keys, fetchedAt: Date.now() };
  return keys;
}

/**
 * @param {Request} request
 */
function readToken(request) {
  const header = request.headers.get('Cf-Access-Jwt-Assertion');
  if (header) return header;
  const cookie = request.headers.get('Cookie') ?? '';
  const match = /(?:^|;\s*)CF_Authorization=([^;]+)/.exec(cookie);
  return match?.[1];
}

/**
 * @typedef {object} AccessEnv
 * @property {string} [ACCESS_TEAM_DOMAIN] 例如 asuka.cloudflareaccess.com
 * @property {string} [ACCESS_AUD] Access 應用程式的 Audience（AUD）標籤
 */

/**
 * @param {Request} request
 * @param {AccessEnv} env
 * @param {typeof fetch} [fetcher]
 * @returns {Promise<{ ok: true, identity: string } | { ok: false, status: number, message: string }>}
 */
export async function verifyAccess(request, env, fetcher = fetch) {
  const team = env.ACCESS_TEAM_DOMAIN?.replace(/^https?:\/\//, '').replace(/\/$/, '');
  const aud = env.ACCESS_AUD;
  if (!team || !aud) {
    return { ok: false, status: 503, message: '尚未設定 Cloudflare Access（ACCESS_TEAM_DOMAIN、ACCESS_AUD），地圖暫不開放。' };
  }
  const token = readToken(request);
  if (!token) return { ok: false, status: 403, message: '需要先通過 Cloudflare Access 登入。' };

  const parts = token.split('.');
  if (parts.length !== 3) return { ok: false, status: 403, message: '登入資訊格式不對。' };
  const [headerPart, payloadPart, signaturePart] = parts;
  let header;
  let payload;
  try {
    header = decodeJson(headerPart);
    payload = decodeJson(payloadPart);
  } catch {
    return { ok: false, status: 403, message: '登入資訊格式不對。' };
  }
  if (header.alg !== 'RS256') return { ok: false, status: 403, message: '登入資訊的簽章方式不對。' };

  const audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!audiences.includes(aud)) return { ok: false, status: 403, message: '登入資訊不是給這個應用程式的。' };
  if (payload.iss !== `https://${team}`) return { ok: false, status: 403, message: '登入資訊的簽發者不對。' };
  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp !== 'number' || payload.exp < now) return { ok: false, status: 403, message: '登入已過期，請重新登入。' };
  if (typeof payload.nbf === 'number' && payload.nbf > now + 60) return { ok: false, status: 403, message: '登入資訊還沒生效。' };

  const keys = await getKeys(team, fetcher);
  const jwk = keys.find((k) => /** @type {any} */ (k).kid === header.kid);
  if (!jwk) {
    keyCache = undefined; // 可能剛換過公鑰，下次重新讀
    return { ok: false, status: 403, message: '找不到對應的公鑰，請重新整理。' };
  }
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const valid = await crypto.subtle.verify(
    'RSASSA-PKCS1-v1_5',
    key,
    base64UrlToBytes(signaturePart),
    new TextEncoder().encode(`${headerPart}.${payloadPart}`),
  );
  if (!valid) return { ok: false, status: 403, message: '登入資訊的簽章不對。' };
  return { ok: true, identity: String(payload.email ?? payload.common_name ?? 'unknown') };
}

/** 測試用：清掉公鑰快取 */
export function resetKeyCache() {
  keyCache = undefined;
}
