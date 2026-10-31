// 測試常用物品清單與時間換算：npm test（在 tools/asuka-toolkit 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORIES, lightBlockId, normalizeItemId } from '../behavior_pack/scripts/catalog.js';
import { clockText, isDaytime } from '../behavior_pack/scripts/clock.js';

test('清單裡的物品 ID 格式正確、沒有重複', () => {
  const ids = CATEGORIES.flatMap((c) => c.items.map((i) => i.id));
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ids) assert.match(id, /^minecraft:[a-z0-9_]+$/);
  for (const c of CATEGORIES) for (const i of c.items) assert.ok(i.amount >= 1 && i.amount <= 64, i.id);
});

test('光源方塊的 ID', () => {
  assert.equal(lightBlockId(15), 'minecraft:light_block_15');
  assert.equal(lightBlockId(0), 'minecraft:light_block_0');
  assert.equal(lightBlockId(99), 'minecraft:light_block_15');
});

test('使用者輸入的物品 ID', () => {
  assert.equal(normalizeItemId(' Barrier '), 'minecraft:barrier');
  assert.equal(normalizeItemId('minecraft:light_block_7'), 'minecraft:light_block_7');
  assert.equal(normalizeItemId('foo:bar'), 'foo:bar');
  assert.equal(normalizeItemId('有空白 的'), undefined);
  assert.equal(normalizeItemId(''), undefined);
});

test('遊戲時間換成時鐘時間', () => {
  assert.equal(clockText(0), '06:00');
  assert.equal(clockText(6000), '12:00');
  assert.equal(clockText(13000), '19:00');
  assert.equal(clockText(18000), '00:00');
  assert.equal(clockText(23500), '05:30');
  assert.equal(isDaytime(1000), true);
  assert.equal(isDaytime(18000), false);
  assert.equal(isDaytime(23800), true);
});
