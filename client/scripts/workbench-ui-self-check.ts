import fs from 'node:fs';

const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const cards = fs.readFileSync('src/workbench/CandidateGrid.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');
const canvas = fs.readFileSync('src/workbench/SentenceCanvas.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');

for (const group of ['direct_syn', 'semantic_related', 'sound_only']) {
  if (!cards.includes(group)) throw new Error(`missing candidate group ${group}`);
}
if (!compare.includes('套用這個選擇') || !page.includes("type: 'apply_candidate'")) {
  throw new Error('candidate apply is not explicit');
}
if (!page.includes('不會替你自動填詞') || !page.includes('不會自動填入字面')) {
  throw new Error('product boundary copy missing');
}
if (!page.includes('limit: 120')) throw new Error('candidate limit must be 120');
if (page.includes("type: 'select', start: 0, width: 1")) {
  throw new Error('creating a line must not auto-select slots');
}
if (!cards.includes('放寬後結果') || !cards.includes('未有足夠近義資料')) {
  throw new Error('relaxed / semantic-gap copy missing');
}
if (!compare.includes('排序順位') || !compare.includes('sourceRank')) {
  throw new Error('compare metadata missing sourceRank');
}
if (!canvas.includes('event.shiftKey') || !canvas.includes('code-summary')) {
  throw new Error('shift-click selection or code summary missing');
}
if (!css.includes('writing-mode: horizontal-tb') || !css.includes('word-break: keep-all')) {
  throw new Error('horizontal candidate/slot layout guard missing');
}
if (!css.includes('flex-wrap: wrap') && !css.includes('auto-fill')) {
  throw new Error('candidate wrapping guard missing');
}

console.log('workbench UI self-check ok');
