// 測試快速建造的方向與座標計算：npm test（在 tools/asuka-toolkit 底下執行）
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  DirectionMode,
  stepFromView,
  linePositions,
  shouldFlip,
  negate,
  parseIntInRange,
  describeDirection,
  faceNormal,
  topPermutationOf,
} from '../behavior_pack/scripts/line.js';

/** 假的方塊狀態：只提供 topPermutationOf 用到的部分 */
function perm(id, states) {
  return {
    states,
    type: { id },
    getState: (name) => states[name],
    withState: (name, value) => perm(id, { ...states, [name]: value }),
  };
}

test('兩格高的方塊：原版的門照抄上面那一格', () => {
  const base = perm('minecraft:spruce_door', { upper_block_bit: false });
  const above = perm('minecraft:spruce_door', { upper_block_bit: true, door_hinge_bit: true });
  assert.equal(topPermutationOf(base, above), above);
});

test('兩格高的方塊：上面不是同一種就沒有上半部', () => {
  const base = perm('minecraft:spruce_door', { upper_block_bit: false });
  assert.equal(topPermutationOf(base, perm('minecraft:air', {})), undefined);
  assert.equal(topPermutationOf(base, undefined), undefined);
});

test('兩格高的方塊：Asuka tech 的門上半可能還沒出現，直接算出來', () => {
  const door = perm('asukatech:door_white', { 'asukatech:upper': false, 'asukatech:hinge_right': true });
  const top = topPermutationOf(door, perm('minecraft:air', {}));
  assert.deepEqual(top.states, { 'asukatech:upper': true, 'asukatech:hinge_right': true });
});

test('一格高的方塊沒有上半部', () => {
  assert.equal(topPermutationOf(perm('minecraft:stone', {}), perm('minecraft:air', {})), undefined);
  assert.equal(topPermutationOf(perm('asukatech:trapdoor_white', { 'asukatech:open': false }), undefined), undefined);
});

/** 由水平角度（0° = 東、90° = 南）與俯仰角（正 = 抬頭）算出視線向量 */
function view(yawDeg, pitchDeg) {
  const yaw = (yawDeg * Math.PI) / 180;
  const pitch = (pitchDeg * Math.PI) / 180;
  return { x: Math.cos(pitch) * Math.cos(yaw), y: Math.sin(pitch), z: Math.cos(pitch) * Math.sin(yaw) };
}

const H = DirectionMode.Horizontal;
const S = DirectionMode.Snap3D;
const F = DirectionMode.Free;

test('水平模式：吸附到八方位', () => {
  assert.deepEqual(stepFromView(view(0, 0), H), { x: 1, y: 0, z: 0 }); // 東
  assert.deepEqual(stepFromView(view(15, 0), H), { x: 1, y: 0, z: 0 }); // 偏一點還是東
  assert.deepEqual(stepFromView(view(90, 0), H), { x: 0, y: 0, z: 1 }); // 南
  assert.deepEqual(stepFromView(view(-45, 0), H), { x: 1, y: 0, z: -1 }); // 東北
  assert.deepEqual(stepFromView(view(-130, 0), H), { x: -1, y: 0, z: -1 }); // 西北
  assert.deepEqual(stepFromView(view(180, 0), H), { x: -1, y: 0, z: 0 }); // 西
});

test('水平模式：低頭看地面放方塊時仍然是水平', () => {
  assert.deepEqual(stepFromView(view(0, -60), H), { x: 1, y: 0, z: 0 });
  assert.deepEqual(stepFromView(view(0, -74), H), { x: 1, y: 0, z: 0 });
});

test('水平模式：看正上方、正下方時改成垂直', () => {
  assert.deepEqual(stepFromView(view(0, 80), H), { x: 0, y: 1, z: 0 });
  assert.deepEqual(stepFromView(view(0, -90), H), { x: 0, y: -1, z: 0 });
});

test('立體模式：45° 斜線與垂直', () => {
  assert.deepEqual(stepFromView(view(90, 40), S), { x: 0, y: 1, z: 1 }); // 往南上方斜
  assert.deepEqual(stepFromView(view(45, -30), S), { x: 1, y: -1, z: 1 }); // 往東南下方斜
  assert.deepEqual(stepFromView(view(90, 10), S), { x: 0, y: 0, z: 1 }); // 接近水平
  assert.deepEqual(stepFromView(view(90, 70), S), { x: 0, y: 1, z: 0 }); // 接近垂直
});

test('自由模式：主軸每步 1 格，其他軸按比例', () => {
  const step = stepFromView({ x: 0.8, y: 0.4, z: 0 }, F);
  assert.deepEqual(step, { x: 1, y: 0.5, z: 0 });
  assert.deepEqual(linePositions({ x: 0, y: 0, z: 0 }, step, 4, 0), [
    { x: 1, y: 1, z: 0 },
    { x: 2, y: 1, z: 0 },
    { x: 3, y: 2, z: 0 },
    { x: 4, y: 2, z: 0 },
  ]);
});

test('自由模式：線是連續的，相鄰兩格最多差 1 格', () => {
  for (const [yaw, pitch] of [[10, 5], [37, -20], [123, 33], [-160, -8], [70, 60]]) {
    const step = stepFromView(view(yaw, pitch), F);
    const points = [{ x: 0, y: 0, z: 0 }, ...linePositions({ x: 0, y: 0, z: 0 }, step, 200, 0)];
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1];
      const b = points[i];
      const d = Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y), Math.abs(a.z - b.z));
      assert.equal(d, 1, `yaw ${yaw} pitch ${pitch} 第 ${i} 格不連續`);
    }
  }
});

test('自由模式：左右對稱的方向長出對稱的線', () => {
  const right = linePositions({ x: 0, y: 0, z: 0 }, stepFromView({ x: 0.9, y: 0, z: 0.3 }, F), 30, 0);
  const left = linePositions({ x: 0, y: 0, z: 0 }, stepFromView({ x: -0.9, y: 0, z: 0.3 }, F), 30, 0);
  assert.deepEqual(left, right.map((p) => ({ x: -p.x || 0, y: p.y, z: p.z })));
});

test('間隔：每顆之間空 gap 格', () => {
  const origin = { x: 10, y: 64, z: -5 };
  assert.deepEqual(linePositions(origin, { x: 1, y: 0, z: 0 }, 3, 0), [
    { x: 11, y: 64, z: -5 },
    { x: 12, y: 64, z: -5 },
    { x: 13, y: 64, z: -5 },
  ]);
  assert.deepEqual(linePositions(origin, { x: 1, y: 0, z: 0 }, 3, 2), [
    { x: 13, y: 64, z: -5 },
    { x: 16, y: 64, z: -5 },
    { x: 19, y: 64, z: -5 },
  ]);
  // 斜線的間隔以「步」計算
  assert.deepEqual(linePositions(origin, { x: 1, y: 0, z: -1 }, 2, 1), [
    { x: 12, y: 64, z: -7 },
    { x: 14, y: 64, z: -7 - 2 },
  ]);
});

test('第一步鑽進貼著的方塊時要反過來', () => {
  const origin = { x: 0, y: 65, z: 0 };
  const ground = { x: 0, y: 64, z: 0 };
  // 看正下方的地面放 → 往上長柱子
  assert.equal(shouldFlip(origin, { x: 0, y: -1, z: 0 }, ground), true);
  assert.deepEqual(negate({ x: 0, y: -1, z: 0 }), { x: 0, y: 1, z: 0 });
  // 看著地面往前放 → 不反轉
  assert.equal(shouldFlip(origin, { x: 1, y: 0, z: 0 }, ground), false);
  // 看著牆面放（牆在東邊）→ 從牆面往外長
  assert.equal(shouldFlip(origin, { x: 1, y: 0, z: 0 }, { x: 1, y: 65, z: 0 }), true);
  // 不知道貼著哪顆時不反轉
  assert.equal(shouldFlip(origin, { x: 0, y: -1, z: 0 }, undefined), false);
});

test('方塊面的法向量', () => {
  assert.deepEqual(faceNormal('Up'), { x: 0, y: 1, z: 0 });
  assert.deepEqual(faceNormal('North'), { x: 0, y: 0, z: -1 });
  assert.equal(faceNormal('Nope'), undefined);
});

test('數字輸入', () => {
  assert.equal(parseIntInRange('100', 1, 1000), 100);
  assert.equal(parseIntInRange(' 5 ', 1, 1000), 5);
  assert.equal(parseIntInRange('5000', 1, 1000), 1000);
  assert.equal(parseIntInRange('0', 1, 1000), 1);
  assert.equal(parseIntInRange('abc', 1, 1000), undefined);
  assert.equal(parseIntInRange('', 0, 10), undefined);
});

test('方向的中文說明', () => {
  assert.equal(describeDirection({ x: 1, y: 0, z: -1 }, H), '東北');
  assert.equal(describeDirection({ x: 0, y: 0, z: 1 }, H), '南');
  assert.equal(describeDirection({ x: 0, y: 1, z: 0 }, H), '正上方');
  assert.equal(describeDirection({ x: -1, y: -1, z: 0 }, S), '西（往下斜）');
  assert.equal(describeDirection({ x: 1, y: 0.1, z: 0.2 }, F), '東，自由角度');
});
