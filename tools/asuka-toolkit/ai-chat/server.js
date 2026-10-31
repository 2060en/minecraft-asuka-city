// 遊戲內 AI 聊天：在 Minecraft 聊天框打字，由 Claude 回答。
//
// 行為包沒辦法對外連網，所以這個功能是一個在電腦上執行的小程式：
// 1. 執行這個程式（雙擊 start.bat），它會在本機開一個 WebSocket 伺服器
// 2. 在遊戲裡輸入 /connect localhost:3000，遊戲就會連過來
// 3. 程式收到玩家的聊天訊息，交給 Claude，再用 tellraw 把回答顯示在聊天框
//
// 這個程式只會送 tellraw、titleraw、querytarget 這幾個指令，不會修改世界。

import { existsSync, mkdirSync, readFileSync, appendFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Anthropic from '@anthropic-ai/sdk';
import { WebSocketServer } from 'ws';
import {
  subscribeMessage,
  commandMessage,
  tellrawCommand,
  actionbarCommand,
  parseIncoming,
  stripMarkdown,
  splitForChat,
  describeQueryTarget,
} from './lib/bedrock.js';
import { loadWorldDocs, buildSystemPrompt } from './lib/prompt.js';
import { ChatSession, describeError, estimateCost } from './lib/chat.js';

const here = dirname(fileURLToPath(import.meta.url));

/**
 * @typedef {object} Config
 * @property {string} apiKey 留空時改用環境變數 ANTHROPIC_API_KEY
 * @property {number} port
 * @property {string} model
 * @property {'low' | 'medium' | 'high' | 'xhigh' | 'max'} effort
 * @property {string} prefix 只回應這個開頭的訊息；空字串代表回應所有聊天
 * @property {boolean} webSearch
 * @property {number} maxHistoryTurns
 * @property {string} repoRoot 設定文件所在的 repo 根目錄（相對於這個資料夾）
 */

/** @type {Config} */
const DEFAULT_CONFIG = {
  apiKey: '',
  port: 3000,
  model: 'claude-opus-5-5',
  effort: 'low',
  prefix: '',
  webSearch: true,
  maxHistoryTurns: 10,
  repoRoot: '../../..',
};

/** @returns {Config} */
function loadConfig() {
  const file = join(here, 'config.json');
  if (!existsSync(file)) return { ...DEFAULT_CONFIG };
  return { ...DEFAULT_CONFIG, ...JSON.parse(readFileSync(file, 'utf8')) };
}

const config = loadConfig();
const apiKey = config.apiKey || process.env.ANTHROPIC_API_KEY;
if (!apiKey) {
  console.error('找不到 API 金鑰。請把 config.example.json 複製成 config.json，填入 apiKey；');
  console.error('或設定環境變數 ANTHROPIC_API_KEY。API 金鑰在 https://platform.claude.com 建立。');
  process.exit(1);
}

const repoRoot = resolve(here, config.repoRoot);
const docs = loadWorldDocs(repoRoot);
const system = buildSystemPrompt(docs);
console.log(`已讀取 ${docs.length} 份設定文件（${system.length.toLocaleString()} 字）：`);
for (const d of docs) console.log(`  ${d.path}`);

const session = new ChatSession({
  client: new Anthropic({ apiKey }),
  model: config.model,
  effort: config.effort,
  system,
  webSearch: config.webSearch,
  maxHistoryTurns: config.maxHistoryTurns,
});

// ---------------------------------------------------------------------------
// 對話紀錄：存在 logs/日期.md，之後可以交給 Claude Code 整理進設定文件
// ---------------------------------------------------------------------------

const logDir = join(here, 'logs');
/**
 * @param {string} who
 * @param {string} text
 */
function writeLog(who, text) {
  mkdirSync(logDir, { recursive: true });
  const now = new Date();
  const date = now.toLocaleDateString('sv-SE'); // YYYY-MM-DD
  const time = now.toLocaleTimeString('sv-SE');
  appendFileSync(join(logDir, `${date}.md`), `**${who}**（${time}）：${text}\n\n`);
}

// ---------------------------------------------------------------------------
// 和遊戲的連線
// ---------------------------------------------------------------------------

const HELP = [
  '§b[Claude]§r 直接在聊天框打字就能跟我聊天。',
  config.prefix ? `只有「${config.prefix}」開頭的訊息才會傳給我。` : '所有聊天訊息都會傳給我（指令不會）。',
  '!reset 開始新的對話；!usage 看這次的用量；!help 看這段說明。',
].join('\n');

/**
 * @param {import('ws').WebSocket} ws
 */
function handleConnection(ws) {
  console.log('Minecraft 已連線');
  /** @type {Map<string, (body: any) => void>} */
  const pending = new Map();
  let queue = Promise.resolve();

  /**
   * 送指令給遊戲，等遊戲回應（最多 5 秒）。
   * @param {string} commandLine
   * @returns {Promise<any>}
   */
  const run = (commandLine) =>
    new Promise((resolveResponse) => {
      const message = commandMessage(commandLine);
      const id = message.header.requestId;
      const timer = setTimeout(() => {
        pending.delete(id);
        resolveResponse(undefined);
      }, 5000);
      pending.set(id, (body) => {
        clearTimeout(timer);
        resolveResponse(body);
      });
      ws.send(JSON.stringify(message));
    });

  /** @param {string} text */
  const say = async (text) => {
    for (const chunk of splitForChat(text)) await run(tellrawCommand(chunk));
  };

  /**
   * @param {string} sender
   * @param {string} message
   */
  const handleChat = async (sender, message) => {
    let text = message.trim();
    if (config.prefix) {
      if (!text.startsWith(config.prefix)) return;
      text = text.slice(config.prefix.length).trim();
    }
    if (!text) return;

    const command = text.replace(/^！/, '!').toLowerCase();
    if (command === '!help') return say(HELP);
    if (command === '!reset') {
      session.reset();
      writeLog('系統', '開始新的對話');
      return say('§b[Claude]§r 已開始新的對話。');
    }
    if (command === '!usage') {
      const u = session.usage;
      const cost = estimateCost(u, config.model);
      return say(
        `§b[Claude]§r 這次啟動以來：${u.requests} 次請求，輸入 ${u.input + u.cacheRead + u.cacheWrite5m + u.cacheWrite1h} token（快取命中 ${u.cacheRead}），輸出 ${u.output} token，搜尋 ${u.webSearches} 次` +
          (cost === undefined ? '' : `，估計 US$${cost.toFixed(3)}`),
      );
    }

    await run(actionbarCommand('§bClaude 思考中…'));
    const position = describeQueryTarget(await run('querytarget @s'));
    const userText = position ? `${text}\n〔遊戲狀態：${position}〕` : text;
    writeLog(sender, text);
    console.log(`${sender}：${text}`);

    try {
      const { reply, refused } = await session.ask(userText);
      if (refused) {
        await say('§b[Claude]§r §7（這個問題沒辦法回答，換個問法試試）');
        return;
      }
      const clean = stripMarkdown(reply);
      writeLog('Claude', clean);
      console.log(`Claude：${clean}`);
      const [first, ...rest] = splitForChat(clean);
      await run(tellrawCommand(`§b[Claude]§r ${first ?? '（沒有回答）'}`));
      for (const chunk of rest) await run(tellrawCommand(chunk));
    } catch (error) {
      const reason = describeError(error);
      console.error(`錯誤：${reason}`);
      await say(`§b[Claude]§r §c${reason}`);
    } finally {
      await run(actionbarCommand(' '));
    }
  };

  ws.on('message', (data) => {
    const incoming = parseIncoming(data.toString());
    if (incoming.kind === 'response') {
      pending.get(incoming.requestId)?.(incoming.body);
      pending.delete(incoming.requestId);
    } else if (incoming.kind === 'chat') {
      // 一次處理一則，避免回答順序亂掉
      queue = queue.then(() => handleChat(incoming.sender, incoming.message)).catch((e) => console.error(e));
    }
  });
  ws.on('close', () => console.log('Minecraft 已中斷連線'));

  ws.send(JSON.stringify(subscribeMessage('PlayerMessage')));
  void say('§b[Claude]§r 已連線！直接在聊天框打字就能跟我聊天，輸入 !help 看說明。');
}

// 只接受本機連線，避免同一個網路的其他裝置連進來用你的 API 額度
const server = new WebSocketServer({ host: '127.0.0.1', port: config.port });
server.on('connection', handleConnection);
server.on('listening', () => {
  console.log('');
  console.log(`準備好了。在 Minecraft 裡輸入：/connect localhost:${config.port}`);
  console.log(`模型：${config.model}（effort: ${config.effort}），網路搜尋：${config.webSearch ? '開' : '關'}`);
});
server.on('error', (error) => {
  console.error(`無法啟動伺服器：${error.message}`);
  process.exit(1);
});
