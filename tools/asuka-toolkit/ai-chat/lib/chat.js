// 和 Claude 的對話：保留最近幾輪對話、呼叫 API、統計用量。

import Anthropic from '@anthropic-ai/sdk';

/**
 * 每百萬 token 的價格（美元），用來估計花費。沒列在這裡的模型只顯示 token 數。
 * 1 小時快取寫入是輸入價格的 2 倍，5 分鐘快取寫入是 1.25 倍。
 * @type {Record<string, { input: number, output: number, cacheRead: number }>}
 */
const PRICES = {
  'claude-opus-5-5': { input: 4, output: 20, cacheRead: 0.2 },
  'claude-sonnet-5-5': { input: 2, output: 10, cacheRead: 0.2 },
};
/** 網路搜尋每次的價格（美元） */
const WEB_SEARCH_PRICE = 0.01;
/** 伺服器端工具（網路搜尋）的回合最多續接幾次 */
const MAX_CONTINUATIONS = 4;

/**
 * @typedef {object} ChatOptions
 * @property {Anthropic} client
 * @property {string} model
 * @property {'low' | 'medium' | 'high' | 'xhigh' | 'max'} effort
 * @property {string} system 系統提示（整個對話期間不變）
 * @property {boolean} webSearch
 * @property {number} maxHistoryTurns 保留最近幾輪對話
 */

/**
 * @typedef {object} Usage
 * @property {number} requests
 * @property {number} input
 * @property {number} output
 * @property {number} cacheRead
 * @property {number} cacheWrite5m
 * @property {number} cacheWrite1h
 * @property {number} webSearches
 */

/** @returns {Usage} */
function emptyUsage() {
  return { requests: 0, input: 0, output: 0, cacheRead: 0, cacheWrite5m: 0, cacheWrite1h: 0, webSearches: 0 };
}

/**
 * @param {Usage} total
 * @param {Anthropic.Beta.BetaUsage} usage
 */
function addUsage(total, usage) {
  total.requests += 1;
  total.input += usage.input_tokens ?? 0;
  total.output += usage.output_tokens ?? 0;
  total.cacheRead += usage.cache_read_input_tokens ?? 0;
  const created = usage.cache_creation;
  if (created) {
    total.cacheWrite5m += created.ephemeral_5m_input_tokens ?? 0;
    total.cacheWrite1h += created.ephemeral_1h_input_tokens ?? 0;
  } else {
    total.cacheWrite1h += usage.cache_creation_input_tokens ?? 0;
  }
  total.webSearches += usage.server_tool_use?.web_search_requests ?? 0;
}

/**
 * 估計花費（美元）；不知道價格的模型回傳 undefined。
 * @param {Usage} u
 * @param {string} model
 */
export function estimateCost(u, model) {
  const p = PRICES[model];
  if (!p) return undefined;
  const perToken = (/** @type {number} */ price) => price / 1_000_000;
  return (
    u.input * perToken(p.input) +
    u.output * perToken(p.output) +
    u.cacheRead * perToken(p.cacheRead) +
    u.cacheWrite5m * perToken(p.input * 1.25) +
    u.cacheWrite1h * perToken(p.input * 2) +
    u.webSearches * WEB_SEARCH_PRICE
  );
}

/**
 * 從回應裡取出文字。
 * @param {Anthropic.Beta.BetaMessage} message
 */
function textOf(message) {
  return message.content
    .filter((b) => b.type === 'text')
    .map((b) => /** @type {Anthropic.Beta.BetaTextBlock} */ (b).text)
    .join('');
}

export class ChatSession {
  /** @param {ChatOptions} options */
  constructor(options) {
    this.options = options;
    /**
     * 對話紀錄只保留文字。思考區塊和搜尋結果不存，這樣刪掉舊的對話時不會讓後面的紀錄失效。
     * @type {Anthropic.Beta.BetaMessageParam[]}
     */
    this.history = [];
    /** 這次啟動以來的用量 */
    this.usage = emptyUsage();
  }

  reset() {
    this.history = [];
  }

  /**
   * 問 Claude 一個問題。
   * @param {string} userText
   * @returns {Promise<{ reply: string, refused: boolean }>}
   */
  async ask(userText) {
    const { client, model, effort, system, webSearch, maxHistoryTurns } = this.options;
    /** @type {Anthropic.Beta.BetaMessageParam[]} */
    let messages = [...this.history, { role: 'user', content: userText }];
    /** @type {Anthropic.Beta.BetaToolUnion[]} */
    const tools = webSearch ? [{ type: 'web_search_20260209', name: 'web_search', max_uses: 3 }] : [];

    let reply = '';
    let refused = false;
    for (let attempt = 0; attempt <= MAX_CONTINUATIONS; attempt++) {
      const response = await client.beta.messages
        .stream({
          model,
          max_tokens: 16000,
          betas: ['server-side-fallback-2026-07-01'],
          fallbacks: 'default',
          output_config: { effort },
          // 系統提示放在 1 小時的快取裡：聊天常常隔好幾分鐘才問一句，5 分鐘的快取會一直過期
          system: [{ type: 'text', text: system, cache_control: { type: 'ephemeral', ttl: '1h' } }],
          ...(tools.length > 0 ? { tools } : {}),
          messages,
        })
        .finalMessage();
      addUsage(this.usage, response.usage);

      if (response.stop_reason === 'refusal') {
        refused = true;
        break;
      }
      reply += textOf(response);
      // 網路搜尋跑太久時會暫停，把回應原封不動接回去，伺服器就會繼續
      if (response.stop_reason === 'pause_turn') {
        messages = [...messages, { role: 'assistant', content: response.content }];
        continue;
      }
      break;
    }

    if (refused) return { reply: '', refused: true };
    reply = reply.trim();
    this.history.push({ role: 'user', content: userText }, { role: 'assistant', content: reply || '（沒有回答）' });
    const keep = maxHistoryTurns * 2;
    if (this.history.length > keep) this.history = this.history.slice(-keep);
    return { reply, refused: false };
  }
}

/**
 * 把 API 錯誤換成給玩家看的說明。
 * @param {unknown} error
 */
export function describeError(error) {
  if (error instanceof Anthropic.AuthenticationError) return 'API 金鑰無效，請檢查 config.json 的 apiKey 或環境變數 ANTHROPIC_API_KEY';
  if (error instanceof Anthropic.PermissionDeniedError) return '這把 API 金鑰沒有使用這個模型的權限';
  if (error instanceof Anthropic.NotFoundError) return '找不到這個模型，請檢查 config.json 的 model';
  if (error instanceof Anthropic.RateLimitError) return '請求太頻繁或額度用完了，稍等一下再試';
  if (error instanceof Anthropic.BadRequestError) return `請求格式有問題：${error.message}`;
  if (error instanceof Anthropic.InternalServerError) return 'Claude 的伺服器暫時有問題，稍後再試';
  if (error instanceof Anthropic.APIConnectionError) return '連不上 Claude API，請檢查網路';
  if (error instanceof Anthropic.APIError) return `API 錯誤 ${error.status}：${error.message}`;
  return String(error);
}
