// 把遊戲的輸入事件換成工具包在意的判斷（純計算，不依賴 @minecraft/server）。

/** 這些情況手也會揮，但不是玩家按左鍵 */
const NOT_LEFT_CLICK = new Set(['Build', 'DropItem', 'Event', 'Interact', 'ThrowItem', 'UseItem']);

/**
 * 這次揮手是不是玩家按左鍵。
 * @param {string} source EntitySwingSource 的值
 */
export function isLeftClickSwing(source) {
  return !NOT_LEFT_CLICK.has(source);
}
