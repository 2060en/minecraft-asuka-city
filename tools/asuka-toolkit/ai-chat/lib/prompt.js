// 讀取 repo 裡的設定文件，組成給 Claude 的系統提示。
// 系統提示在程式啟動時組好就不再改變，這樣提示快取（prompt caching）才會一直命中。
// 改了文件之後，重新啟動程式就會讀到新的內容。

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

/**
 * @param {string} dir
 * @returns {string[]}
 */
function listMarkdown(dir) {
  return readdirSync(dir)
    .sort()
    .flatMap((name) => {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) return listMarkdown(path);
      return name.endsWith('.md') ? [path] : [];
    });
}

/**
 * 讀取 CLAUDE.md 和 docs/ 底下所有的 Markdown 文件。
 * @param {string} repoRoot
 * @returns {{ path: string, text: string }[]}
 */
export function loadWorldDocs(repoRoot) {
  const files = [join(repoRoot, 'CLAUDE.md'), ...listMarkdown(join(repoRoot, 'docs'))];
  return files.map((file) => ({
    path: relative(repoRoot, file).split(sep).join('/'),
    text: readFileSync(file, 'utf8').trim(),
  }));
}

const INSTRUCTIONS = `你是作者在 Minecraft 裡的聊天夥伴。作者在 Minecraft 基岩版建造了約 10 年的架空島國「津蘭賀千良」（首都 Asuka City），設定都記在下面的文件裡。作者在遊戲聊天框打字跟你說話，你的回答會顯示在遊戲聊天框。

回答方式：
・一律使用繁體中文（台灣用語）。
・遊戲聊天框很窄，也不支援 Markdown：只用純文字，不要用 #、**、表格、程式碼區塊；需要條列時每行用「・」開頭。
・這是即時聊天，請馬上開始回答，通常 2～5 句就好；作者要求詳細說明時再寫長一點。
・作者的訊息後面如果有「〔遊戲狀態：…〕」，那是程式自動附上的座標和維度，不是作者打的字。只在有關係的時候才提到。
・需要查現實資料（建築高度、車站規模、交通數據等）時可以用網路搜尋。

關於設定：
・下面的文件是正典。回答設定問題以文件為準；文件沒有寫的，先說「文件裡沒有」，再提出建議並標明是建議。
・討論設定時遵守 CLAUDE.md 的設計原則：用現實先例檢驗合理性、量體配合人口規模、提出名字前先查命名黑名單、名字的漢字用日文漢字。
・你不能修改文件，也不能執行遊戲指令。聊天中討論出的新設定不會自動記錄；作者確認了新設定時，提醒作者之後用 Claude Code 整理進 repo。`;

/**
 * 組成系統提示。
 * @param {{ path: string, text: string }[]} docs
 */
export function buildSystemPrompt(docs) {
  const documents = docs.map((d) => `<document path="${d.path}">\n${d.text}\n</document>`).join('\n\n');
  return `${INSTRUCTIONS}\n\n以下是設定文件：\n\n<documents>\n${documents}\n</documents>`;
}
