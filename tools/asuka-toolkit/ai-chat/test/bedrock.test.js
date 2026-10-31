// 測試 WebSocket 協定與文字處理：npm test（在 tools/asuka-toolkit/ai-chat 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  subscribeMessage,
  commandMessage,
  tellrawCommand,
  parseIncoming,
  stripMarkdown,
  splitForChat,
  describeQueryTarget,
} from '../lib/bedrock.js';
import { buildSystemPrompt } from '../lib/prompt.js';
import { estimateCost } from '../lib/chat.js';

test('訂閱與指令訊息的格式', () => {
  const sub = subscribeMessage('PlayerMessage');
  assert.equal(sub.header.messagePurpose, 'subscribe');
  assert.equal(sub.body.eventName, 'PlayerMessage');
  const cmd = commandMessage('say hi');
  assert.equal(cmd.header.messagePurpose, 'commandRequest');
  assert.equal(cmd.body.commandLine, 'say hi');
  assert.notEqual(cmd.header.requestId, commandMessage('say hi').header.requestId);
});

test('tellraw 會正確跳脫引號', () => {
  const line = tellrawCommand('他說"你好"\\');
  assert.equal(line, 'tellraw @a {"rawtext":[{"text":"他說\\"你好\\"\\\\"}]}');
  assert.deepEqual(JSON.parse(line.slice('tellraw @a '.length)), { rawtext: [{ text: '他說"你好"\\' }] });
});

test('只處理玩家自己打的聊天', () => {
  const chat = JSON.stringify({ header: { eventName: 'PlayerMessage', messagePurpose: 'event' }, body: { message: '首都在哪', sender: 'Ian', type: 'chat' } });
  assert.deepEqual(parseIncoming(chat), { kind: 'chat', sender: 'Ian', message: '首都在哪' });
  const tellraw = JSON.stringify({ header: { eventName: 'PlayerMessage', messagePurpose: 'event' }, body: { message: '[Claude] 你好', sender: '', type: 'tellraw' } });
  assert.equal(parseIncoming(tellraw).kind, 'other');
  const say = JSON.stringify({ header: { eventName: 'PlayerMessage', messagePurpose: 'event' }, body: { message: 'hi', sender: 'External', type: 'say' } });
  assert.equal(parseIncoming(say).kind, 'other');
  const response = JSON.stringify({ header: { messagePurpose: 'commandResponse', requestId: 'abc' }, body: { statusCode: 0 } });
  assert.deepEqual(parseIncoming(response), { kind: 'response', requestId: 'abc', body: { statusCode: 0 } });
  assert.equal(parseIncoming('not json').kind, 'other');
});

test('拿掉 Markdown', () => {
  assert.equal(stripMarkdown('## 標題\n**粗體** 和 `程式`\n- 第一點\n* 第二點'), '標題\n粗體 和 程式\n・第一點\n・第二點');
  assert.equal(stripMarkdown('看[這裡](https://example.com)'), '看這裡（https://example.com）');
});

test('長回答切段，中文字算一個字', () => {
  assert.deepEqual(splitForChat('第一行\n\n第二行'), ['第一行', '第二行']);
  const long = '飛'.repeat(400);
  const chunks = splitForChat(long, 180);
  assert.deepEqual(chunks.map((c) => Array.from(c).length), [180, 180, 40]);
  assert.equal(chunks.join(''), long);
});

test('讀出玩家位置', () => {
  const body = { statusCode: 0, details: JSON.stringify([{ dimension: 0, position: { x: 120.7, y: 64, z: -35.2 }, yRot: 90 }]) };
  assert.equal(describeQueryTarget(body), '座標 (120, 64, -36)，主世界');
  assert.equal(describeQueryTarget({ statusCode: -1 }), undefined);
  assert.equal(describeQueryTarget(undefined), undefined);
});

test('系統提示包含所有文件，而且每次組出來都一樣（快取才會命中）', () => {
  const docs = [{ path: 'CLAUDE.md', text: '原則' }, { path: 'docs/world/naming.md', text: '黑名單' }];
  const a = buildSystemPrompt(docs);
  assert.equal(a, buildSystemPrompt(docs));
  assert.match(a, /<document path="docs\/world\/naming.md">\n黑名單\n<\/document>/);
});

test('估計花費', () => {
  const u = { requests: 1, input: 1_000_000, output: 1_000_000, cacheRead: 1_000_000, cacheWrite5m: 0, cacheWrite1h: 1_000_000, webSearches: 10 };
  assert.equal(estimateCost(u, 'claude-opus-5-5')?.toFixed(2), (4 + 20 + 0.2 + 8 + 0.1).toFixed(2));
  assert.equal(estimateCost(u, 'some-other-model'), undefined);
});
