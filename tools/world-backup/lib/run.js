// 執行外部程式（restic、uNmINeD、rclone）的小工具。

import { spawn, execFileSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { basename, delimiter, join } from 'node:path';
import { createInterface } from 'node:readline/promises';

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
 * 問使用者一個問題。不是在視窗裡執行（例如被其他程式呼叫）就直接回傳空字串。
 * @param {string} question
 */
export async function ask(question) {
  if (!process.stdin.isTTY) return '';
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    return (await rl.question(question)).trim();
  } finally {
    rl.close();
  }
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
 * 找外部程式的完整路徑。winget 裝的 restic 檔名帶版本號（restic_0.19.1_windows_amd64.exe），
 * 也不一定建得出 restic 這個別名，所以 PATH 找不到時，到 winget 的安裝資料夾找。
 * 哪裡都找不到就原樣回傳，讓執行時報錯。
 * @param {string} exe 程式名稱或完整路徑
 * @param {NodeJS.ProcessEnv} [env]
 */
export function findExe(exe, env = process.env) {
  if (/[\\/]/.test(exe)) return exe;
  for (const dir of (env.PATH ?? env.Path ?? '').split(delimiter)) {
    if (dir && existsSync(join(dir, `${exe}.exe`))) return join(dir, `${exe}.exe`);
  }
  if (!env.LOCALAPPDATA) return exe;
  const packages = join(env.LOCALAPPDATA, 'Microsoft', 'WinGet', 'Packages');
  if (!existsSync(packages)) return exe;
  const name = new RegExp(`^${exe}([-_.].*)?\\.exe$`, 'i');
  const found = readdirSync(packages)
    .filter((folder) => folder.toLowerCase().startsWith(`${exe.toLowerCase()}.`))
    .flatMap((folder) =>
      readdirSync(join(packages, folder), { recursive: true, encoding: 'utf8' })
        .filter((file) => name.test(basename(file)))
        .map((file) => join(packages, folder, file)),
    )
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  return found.at(-1) ?? exe;
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
