// Minecraft 基岩版 WebSocket（/connect）協定的小工具。純計算，不需要連線就能測試。
//
// 遊戲輸入 /connect localhost:3000 之後，遊戲會連到這個程式。
// 程式可以訂閱事件（例如玩家聊天 PlayerMessage），也可以送指令給遊戲執行（例如 tellraw）。

import { randomUUID } from 'node:crypto';

/**
 * 訂閱遊戲事件的訊息。
 * @param {string} eventName 例如 PlayerMessage
 */
export function subscribeMessage(eventName) {
  return {
    header: { version: 1, requestId: randomUUID(), messageType: 'commandRequest', messagePurpose: 'subscribe' },
    body: { eventName },
  };
}

/**
 * 請遊戲執行指令的訊息。
 * @param {string} commandLine 不含開頭的斜線
 */
export function commandMessage(commandLine) {
  return {
    header: { version: 1, requestId: randomUUID(), messageType: 'commandRequest', messagePurpose: 'commandRequest' },
    body: { version: 1, commandLine, origin: { type: 'player' } },
  };
}

/**
 * 在聊天框顯示文字的指令。
 * @param {string} text
 * @param {string} [target]
 */
export function tellrawCommand(text, target = '@a') {
  return `tellraw ${target} ${JSON.stringify({ rawtext: [{ text }] })}`;
}

/**
 * 在快捷欄上方顯示文字的指令。
 * @param {string} text
 * @param {string} [target]
 */
export function actionbarCommand(text, target = '@a') {
  return `titleraw ${target} actionbar ${JSON.stringify({ rawtext: [{ text }] })}`;
}

/**
 * 解析遊戲送來的訊息。
 * @param {string} raw
 * @returns {{ kind: 'chat', sender: string, message: string }
 *   | { kind: 'response', requestId: string, body: any }
 *   | { kind: 'other' }}
 */
export function parseIncoming(raw) {
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return { kind: 'other' };
  }
  const header = data?.header ?? {};
  const body = data?.body ?? {};
  if (header.messagePurpose === 'commandResponse' || header.messagePurpose === 'error') {
    return { kind: 'response', requestId: String(header.requestId ?? ''), body };
  }
  if (header.eventName === 'PlayerMessage' && header.messagePurpose === 'event') {
    // type 是 chat 才是玩家自己打的字；tellraw、say 等指令產生的訊息不處理，避免自己回自己
    const type = body.type ?? 'chat';
    if (type !== 'chat') return { kind: 'other' };
    const sender = String(body.sender ?? '');
    const message = String(body.message ?? '');
    if (!sender || sender === 'External' || !message) return { kind: 'other' };
    return { kind: 'chat', sender, message };
  }
  return { kind: 'other' };
}

/**
 * 遊戲聊天框不支援 Markdown，把常見的 Markdown 符號拿掉。
 * @param {string} text
 */
export function stripMarkdown(text) {
  return text
    .replace(/```[a-z]*\n?/gi, '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*[-*]\s+/gm, '・')
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '$1（$2）')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * 把長回答切成好幾段，每段不超過 maxLength 個字（中文字也算一個字）。
 * 先照換行切，太長的行再照字數切。
 * @param {string} text
 * @param {number} [maxLength]
 * @returns {string[]}
 */
export function splitForChat(text, maxLength = 180) {
  const chunks = [];
  for (const line of text.split('\n')) {
    const chars = Array.from(line);
    if (chars.length === 0) continue;
    for (let i = 0; i < chars.length; i += maxLength) chunks.push(chars.slice(i, i + maxLength).join(''));
  }
  return chunks;
}

/** querytarget 回傳的維度編號 */
const DIMENSIONS = ['主世界', '地獄', '終界'];

/**
 * 從 querytarget 指令的回應讀出玩家位置。
 * @param {any} body
 * @returns {string | undefined} 例如「座標 (120, 64, -35)，主世界」
 */
export function describeQueryTarget(body) {
  try {
    const details = typeof body?.details === 'string' ? JSON.parse(body.details) : body?.details;
    const target = Array.isArray(details) ? details[0] : undefined;
    const p = target?.position;
    if (!p) return undefined;
    const pos = `座標 (${Math.floor(p.x)}, ${Math.floor(p.y)}, ${Math.floor(p.z)})`;
    const dim = DIMENSIONS[target.dimension];
    return dim ? `${pos}，${dim}` : pos;
  } catch {
    return undefined;
  }
}
