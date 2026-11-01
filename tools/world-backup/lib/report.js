// 備份紀錄：每次備份在 docs/backup-log.md 的表格加一行。

export const REPORT_HEADER = `# 備份紀錄

由 \`tools/world-backup/backup.js\` 自動產生，每次備份加一行。

| 日期 | 備註 | restic 快照 | 世界大小 | 新增資料 | 地圖 | 圖磚（新上傳） |
| --- | --- | --- | --- | --- | --- | --- |
`;

/**
 * @param {number} bytes
 */
export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  const value = bytes / 1024 ** i;
  return `${value >= 100 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

/**
 * @param {string} text
 */
function cell(text) {
  return text.replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

/**
 * @param {object} input
 * @param {Date} input.date
 * @param {string} input.note
 * @param {{ snapshot: string, worldBytes: number, addedBytes: number }} [input.backup]
 * @param {{ id: string, tiles: number, newTiles: number }} [input.map]
 */
export function reportRow({ date, note, backup, map }) {
  const pad = (/** @type {number} */ n) => String(n).padStart(2, '0');
  const when = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  const cols = [
    when,
    cell(note) || '—',
    backup ? `\`${backup.snapshot}\`` : '—',
    backup ? formatBytes(backup.worldBytes) : '—',
    backup ? formatBytes(backup.addedBytes) : '—',
    map ? `\`${map.id}\`` : '—',
    map ? `${map.tiles}（${map.newTiles}）` : '—',
  ];
  return `| ${cols.join(' | ')} |\n`;
}
