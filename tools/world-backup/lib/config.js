// 讀設定檔。設定檔放在 repo 外面（%USERPROFILE%/.config/asuka/world-backup.json），
// 和密碼檔同一個資料夾，這樣換分支、換工作資料夾都不用重設。

import { existsSync, readFileSync } from 'node:fs';
import { delimiter, dirname, isAbsolute, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expandEnv, findExe } from './run.js';

const toolDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const configFile = resolve(expandEnv('%USERPROFILE%/.config/asuka/world-backup.json'));

/**
 * rclone 的設定（Google 憑證與權杖）。不放 rclone 預設的 %APPDATA%：從 Claude 桌面版啟動的程式
 * 寫進 %APPDATA% 時，Windows 會導到 Claude 專屬的資料夾，作者雙擊時就找不到（2026-11-05 實際遇到）。
 */
export const rcloneConfigFile = resolve(expandEnv('%USERPROFILE%/.config/asuka/rclone.conf'));

/**
 * @typedef {object} Config
 * @property {string} worldPath
 * @property {string[]} minecraftProcesses
 * @property {{ exe: string, repository: string, passwordFile: string, forget: string[] }} restic
 * @property {{ exe: string, extraArgs: string[] }} unmined
 * @property {{ exe: string, remote: string, extraArgs: string[] }} rclone
 * @property {{ enabled?: boolean, renderDir: string, stateDir: string }} map
 * @property {string} reportFile
 */

/** @returns {Config} */
export function loadConfig() {
  if (!existsSync(configFile)) {
    console.error(`找不到設定檔 ${configFile}。請把 config.example.json 複製過去，填入路徑。`);
    process.exit(1);
  }
  /** @type {Config} */
  const config = JSON.parse(readFileSync(configFile, 'utf8'));
  const path = (/** @type {string} */ p) => resolve(toolDir, expandEnv(p));
  config.worldPath = path(config.worldPath);
  config.restic.passwordFile = config.restic.passwordFile ? path(config.restic.passwordFile) : '';
  config.map.renderDir = path(config.map.renderDir);
  config.map.stateDir = path(config.map.stateDir);
  config.reportFile = path(config.reportFile);
  config.restic.exe = findExe(expandEnv(config.restic.exe));
  config.unmined.exe = findExe(expandEnv(config.unmined.exe));
  config.rclone.exe = findExe(expandEnv(config.rclone.exe));
  return config;
}

/**
 * 執行 restic 要用的環境變數。restic 靠 PATH 找 rclone，所以把 rclone 的資料夾放到最前面。
 * 不用 -o rclone.program：實測給 Windows 路徑時 restic 只拿到「C:」，執行失敗。
 * @param {Pick<Config, 'restic' | 'rclone'>} config
 * @param {NodeJS.ProcessEnv} [env]
 */
export function resticEnv(config, env = process.env) {
  const pathKey = Object.keys(env).find((key) => key.toLowerCase() === 'path') ?? 'PATH';
  return {
    RESTIC_REPOSITORY: config.restic.repository,
    RCLONE_CONFIG: rcloneConfigFile,
    ...(config.restic.passwordFile ? { RESTIC_PASSWORD_FILE: config.restic.passwordFile } : {}),
    ...(isAbsolute(config.rclone.exe) ? { [pathKey]: `${dirname(config.rclone.exe)}${delimiter}${env[pathKey] ?? ''}` } : {}),
  };
}
