// 讀設定檔。設定檔放在 repo 外面（%USERPROFILE%/.config/asuka/world-backup.json），
// 和密碼檔同一個資料夾，這樣換分支、換工作資料夾都不用重設。

import { copyFileSync, existsSync, readFileSync } from 'node:fs';
import { delimiter, dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expandEnv, findExe } from './run.js';

const toolDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const configFile = resolve(expandEnv('%USERPROFILE%/.config/asuka/world-backup.json'));

/**
 * rclone 的設定（Google 憑證與權杖）。不放 rclone 預設的 %APPDATA%：從 Claude 桌面版啟動的程式
 * 寫進 %APPDATA% 時，Windows 會導到 Claude 專屬的資料夾，作者雙擊時就找不到（2026-11-05 實際遇到）。
 */
export const rcloneConfigFile = resolve(expandEnv('%USERPROFILE%/.config/asuka/rclone.conf'));

/** 地圖的外觀（uNmINeD 電腦版存出來的格式），見 README「地圖的外觀」 */
export const mapSettingsFile = resolve(toolDir, 'unmined/map-settings.json');
const blockStylesFile = resolve(toolDir, 'unmined/custom.blockstyles.txt');

/**
 * @typedef {object} Config
 * @property {string} worldPath
 * @property {string[]} minecraftProcesses
 * @property {{ exe: string, repository: string, passwordFile: string, forget: string[] }} restic
 * @property {{ exe: string, extraArgs: string[] }} unmined
 * @property {{ exe: string, remote: string, r2Endpoint?: string, extraArgs: string[] }} rclone
 * @property {{ enabled?: boolean, url?: string, renderDir: string, stateDir: string }} map
 * @property {string} reportFile
 */

/**
 * uNmINeD 渲染網頁地圖的參數。
 * - 一律 --force：它判斷「有沒有變動」時看不到 LevelDB 的 .log，而基岩版關遊戲時最新的改動就只在 .log，
 *   不強制的話地圖會停在舊的樣子（2026-11-05 實測）。內容相同的圖磚編碼結果也相同，所以不會多傳。
 * - 預設的 JPEG 在 0.20.11-dev 一存檔就當掉（InvalidOperation_NoValue），所以沒指定格式時用 WebP（無損）。
 * - 預設每張圖磚印一行，一次幾千行，所以只顯示警告以上。
 * - 外觀固定：3d 影子，水和草不隨生態域變色（作者決定，網頁上沒有開關）。
 * @param {Pick<Config, 'worldPath' | 'unmined' | 'map'>} config
 */
export function unminedRenderArgs(config) {
  const { extraArgs } = config.unmined;
  const unlessGiven = (/** @type {string} */ name, /** @type {string} */ value) => (extraArgs.some((a) => a.startsWith(`--${name}`)) ? [] : [`--${name}=${value}`]);
  return ['web', 'render', `--world=${config.worldPath}`, `--output=${config.map.renderDir}`, '--force', ...unlessGiven('imageformat', 'webp'), ...unlessGiven('mapsettings', mapSettingsFile), ...unlessGiven('shadows', '3d'), ...unlessGiven('log-level', 'warning'), ...extraArgs];
}

/**
 * uNmINeD 只讀自己 config 資料夾裡的 custom.blockstyles.txt，沒有參數可以指定別的位置，
 * 所以每次渲染前複製過去（更新 uNmINeD 把它蓋掉時也會補回來）。
 * @param {string} unminedExe
 */
export function installBlockStyles(unminedExe) {
  copyFileSync(blockStylesFile, join(dirname(unminedExe), 'config', 'custom.blockstyles.txt'));
}

/**
 * 從 Cloudflare 顯示的 S3 API 網址取出 R2 端點。網址後面可能帶著 bucket 名稱，一律去掉。
 * @param {string} text
 * @returns {string | undefined}
 */
export function parseR2Endpoint(text) {
  const m = /^https:\/\/([0-9a-f]{32})(\.[a-z]+)?\.r2\.cloudflarestorage\.com(\/.*)?$/i.exec(text.trim());
  return m ? `https://${m[1]}${m[2] ?? ''}.r2.cloudflarestorage.com` : undefined;
}

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
