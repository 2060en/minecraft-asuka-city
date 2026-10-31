// 時間與天氣：一鍵切換白天／晚上、設定時間、開關時間流動與天氣變化。

import { world, WeatherType } from '@minecraft/server';
import { ActionFormData, ModalFormData } from '@minecraft/server-ui';
import { notify, showForm } from './ui.js';
import { clockText, isDaytime } from './clock.js';

/** @typedef {import('@minecraft/server').Player} Player */
/** @typedef {(player: Player) => Promise<void>} Back */

/** 時間點（遊戲刻，一天 24000） */
const TIME_PRESETS = [
  { label: '日出', time: 23000 },
  { label: '白天', time: 1000 },
  { label: '正午', time: 6000 },
  { label: '日落', time: 12000 },
  { label: '晚上', time: 13000 },
  { label: '半夜（最暗，看燈光用）', time: 18000 },
];

/**
 * @param {Player} player
 * @param {number} time
 * @param {string} label
 */
function setTime(player, time, label) {
  world.setTimeOfDay(time);
  notify(player, `§a時間：${label}（${clockText(time)}）`);
}

/**
 * @param {Player} player
 * @param {Back} back
 */
async function openCustomTime(player, back) {
  const now = world.getTimeOfDay();
  const form = new ModalFormData()
    .title('自訂時間')
    .slider('時間（遊戲刻，0 = 早上 6 點，6000 = 正午，18000 = 半夜）', 0, 23900, {
      defaultValue: Math.round(now / 100) * 100,
      valueStep: 100,
    })
    .submitButton('設定');
  const response = await showForm(player, form);
  if (!response || response.canceled || !response.formValues) return back(player);
  const time = Number(response.formValues[0]);
  setTime(player, time, `${time}`);
}

/**
 * @param {Player} player
 * @param {Back} [onBack]
 */
export async function openEnvironmentMenu(player, onBack) {
  const self = () => openEnvironmentMenu(player, onBack);
  const rules = world.gameRules;
  const now = world.getTimeOfDay();
  const day = isDaytime(now);

  /** @type {{ label: string, run: () => void | Promise<void> }[]} */
  const actions = [
    day
      ? { label: '§1切到半夜（看燈光）', run: () => setTime(player, 18000, '半夜') }
      : { label: '§6切回白天', run: () => setTime(player, 1000, '白天') },
    ...TIME_PRESETS.map((p) => ({ label: `${p.label}（${clockText(p.time)}）`, run: () => setTime(player, p.time, p.label) })),
    { label: '自訂時間…', run: () => openCustomTime(player, self) },
    {
      label: rules.doDayLightCycle ? '時間流動：§a開§r（按一下固定時間）' : '時間流動：§c關§r（按一下恢復流動）',
      run: () => {
        rules.doDayLightCycle = !rules.doDayLightCycle;
        notify(player, rules.doDayLightCycle ? '§a時間開始流動' : '§7時間已固定');
      },
    },
    {
      label: '天氣：晴天',
      run: () => {
        player.dimension.setWeather(WeatherType.Clear);
        notify(player, '§a天氣：晴天');
      },
    },
    {
      label: '天氣：下雨',
      run: () => {
        player.dimension.setWeather(WeatherType.Rain);
        notify(player, '§a天氣：下雨');
      },
    },
    {
      label: '天氣：雷雨',
      run: () => {
        player.dimension.setWeather(WeatherType.Thunder);
        notify(player, '§a天氣：雷雨');
      },
    },
    {
      label: rules.doWeatherCycle ? '天氣變化：§a開§r（按一下固定天氣）' : '天氣變化：§c關§r（按一下恢復變化）',
      run: () => {
        rules.doWeatherCycle = !rules.doWeatherCycle;
        notify(player, rules.doWeatherCycle ? '§a天氣開始變化' : '§7天氣已固定');
      },
    },
  ];

  const form = new ActionFormData()
    .title('時間與天氣')
    .body(`現在：${clockText(now)}（${now}）${rules.doDayLightCycle ? '' : '，時間固定中'}`);
  for (const a of actions) form.button(a.label);
  form.button('返回');
  const response = await showForm(player, form);
  if (!response || response.canceled || response.selection === undefined) return;
  const action = actions[response.selection];
  if (action) await action.run();
  else if (onBack) await onBack(player);
}
