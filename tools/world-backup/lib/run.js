// 執行外部程式（restic、uNmINeD、rclone）的小工具。

import { spawn, execFileSync } from 'node:child_process';

/**
 * 執行程式，輸出直接顯示在視窗上。
 * @param {string} exe
 * @param {string[]} args
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {Promise<void>}
 */
export function runVisible(exe, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(exe, args, { stdio: 'inherit', env: { ...process.env, ...env } });
    child.on('error', (error) => reject(new Error(`無法執行 ${exe}：${error.message}`)));
    child.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`${exe} 結束時回傳 ${code}`))));
  });
}

/**
 * 執行程式，一行一行讀取它的輸出。錯誤訊息直接顯示在視窗上。
 * @param {string} exe
 * @param {string[]} args
 * @param {(line: string) => void} onLine
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {Promise<void>}
 */
export function runLines(exe, args, onLine, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(exe, args, { stdio: ['inherit', 'pipe', 'inherit'], env: { ...process.env, ...env } });
    let buffer = '';
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', (chunk) => {
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';
      for (const line of lines) if (line) onLine(line);
    });
    child.on('error', (error) => reject(new Error(`無法執行 ${exe}：${error.message}`)));
    child.on('close', (code) => {
      if (buffer) onLine(buffer);
      code === 0 ? resolve() : reject(new Error(`${exe} 結束時回傳 ${code}`));
    });
  });
}

/**
 * Windows 上 Minecraft 是不是還開著。其他系統一律回傳 false。
 * @param {string[]} processNames 例如 Minecraft.Windows.exe
 */
export function isRunning(processNames) {
  if (process.platform !== 'win32') return false;
  const output = execFileSync('tasklist', ['/FO', 'CSV', '/NH'], { encoding: 'utf8' });
  const running = new Set(
    output
      .split(/\r?\n/)
      .map((line) => line.split('","')[0]?.replace(/^"/, '').toLowerCase())
      .filter(Boolean),
  );
  return processNames.some((name) => running.has(name.toLowerCase()));
}

/**
 * 把字串裡的 %APPDATA% 這類 Windows 環境變數換成實際的值。
 * @param {string} text
 * @param {NodeJS.ProcessEnv} [env]
 */
export function expandEnv(text, env = process.env) {
  return text.replace(/%([A-Za-z_][A-Za-z0-9_]*)%/g, (whole, name) => {
    const key = Object.keys(env).find((k) => k.toLowerCase() === name.toLowerCase());
    return key ? String(env[key]) : whole;
  });
}
