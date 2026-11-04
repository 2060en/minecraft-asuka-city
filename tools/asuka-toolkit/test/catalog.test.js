// 測試旋風棒的特殊物品清單與左鍵判斷：npm test（在 tools/asuka-toolkit 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SPECIAL_ITEMS } from '../behavior_pack/scripts/catalog.js';
import { isLeftClickSwing } from '../behavior_pack/scripts/input.js';

test('特殊物品是作者選的 7 樣（2026-11-05）', () => {
  assert.deepEqual(
    SPECIAL_ITEMS.map((i) => i.id),
    [
      'minecraft:structure_block',
      'minecraft:structure_void',
      'minecraft:barrier',
      'minecraft:light_block_15',
      'minecraft:command_block',
      'minecraft:repeating_command_block',
      'minecraft:chain_command_block',
    ],
  );
  for (const item of SPECIAL_ITEMS) {
    assert.ok(item.label.length > 0);
    assert.ok(item.amount >= 1 && item.amount <= 64);
  }
});

test('只有左鍵才算揮一下', () => {
  for (const source of ['Attack', 'Mine', 'None']) assert.equal(isLeftClickSwing(source), true, source);
  // 放方塊、右鍵互動、丟東西也會揮手，但不能開介面
  for (const source of ['Build', 'DropItem', 'Event', 'Interact', 'ThrowItem', 'UseItem']) {
    assert.equal(isLeftClickSwing(source), false, source);
  }
});
