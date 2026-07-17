import fs from 'node:fs';

const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const cards = fs.readFileSync('src/workbench/CandidateGrid.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');
const canvas = fs.readFileSync('src/workbench/SentenceCanvas.tsx', 'utf8');
const constraints = fs.readFileSync('src/workbench/ConstraintBar.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const app = fs.readFileSync('src/App.tsx', 'utf8');
const detail = fs.readFileSync('src/entry-detail/EntryDetailPanel.tsx', 'utf8');

for (const group of ['direct_syn', 'semantic_related', 'sound_only']) {
  if (!cards.includes(group)) throw new Error(`missing candidate group ${group}`);
}
if (!compare.includes('套用這個選擇') || !page.includes("type: 'apply_candidate'")) {
  throw new Error('candidate apply is not explicit');
}
if (!compare.includes('在搜尋頁查看') || !compare.includes('onOpenInSearch')) {
  throw new Error('open-in-search missing from compare panel');
}
if (!page.includes('不會替你自動填詞') || !page.includes('不會自動填入字面')) {
  throw new Error('product boundary copy missing');
}
if (!page.includes('limit: 120')) throw new Error('candidate limit must be 120');
if (page.includes("type: 'select', start: 0, width: 1")) {
  throw new Error('creating a line must not auto-select slots');
}
if (!page.includes('consumeIngest') || !page.includes('writeOpenSearch')) {
  throw new Error('workbench bridge consume/write missing');
}
if (!page.includes('toggleLockKeepingSpan') || !constraints.includes('空白鍵鎖')) {
  throw new Error('click-lock / shortcut hint missing');
}
if (!constraints.includes('整段押韻') || !constraints.includes('整段同聲母')) {
  throw new Error('phoneme dim whole labels missing');
}
if (constraints.includes('末格同韻') || constraints.includes('首格同聲')) {
  throw new Error('legacy end-anchor buttons must be removed');
}
if (!cards.includes('放寬後結果') || !cards.includes('未有足夠近義資料')) {
  throw new Error('relaxed / semantic-gap copy missing');
}
if (!compare.includes('排序順位') || !compare.includes('sourceRank')) {
  throw new Error('compare metadata missing sourceRank');
}
if (!canvas.includes('onToggleLock') || !canvas.includes('code-summary') || !canvas.includes('is-in-span')) {
  throw new Error('click-lock canvas or code summary missing');
}
if (!detail.includes('放入句格') || !app.includes('PutInWorkbenchModal') || !app.includes('openSearchTabWithQuery')) {
  throw new Error('put-in-workbench / open-search wiring missing');
}
if (!css.includes('writing-mode: horizontal-tb') || !css.includes('word-break: keep-all')) {
  throw new Error('horizontal candidate/slot layout guard missing');
}
if (!css.includes('flex-wrap: wrap') && !css.includes('auto-fill')) {
  throw new Error('candidate wrapping guard missing');
}

console.log('workbench UI self-check ok');
