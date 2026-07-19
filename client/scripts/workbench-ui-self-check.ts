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
if (!page.includes('hydrateDraftCodes') || !page.includes('pendingResolve')) {
  throw new Error('code hydrate / reading retry missing');
}
if (!page.includes('toggleLockKeepingSpan') || !constraints.includes('空白鍵標定')) {
  throw new Error('click-span mark / shortcut hint missing');
}
if (page.includes('slot.locked && slot.surface')) {
  throw new Error('lock must not emit literal_char');
}
if (!constraints.includes('整段押韻') || !constraints.includes('整段同聲母')) {
  throw new Error('phoneme dim whole labels missing');
}
if (!constraints.includes('同音（預設）') || !constraints.includes('不限定') || !constraints.includes('指定碼')) {
  throw new Error('code constraint mode options missing');
}
if (!constraints.includes('constraint-bar__menus') || !constraints.includes('constraint-bar__explicit')) {
  throw new Error('wide menu row / explicit slot structure missing');
}
if (!constraints.includes('is-reserved') || !constraints.includes('is-active')) {
  throw new Error('explicit code slot must reserve height when inactive');
}
if (!page.includes('codeConstraint') || !page.includes('buildCodeDigitSlots')) {
  throw new Error('code constraint wiring missing');
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
if (!canvas.includes('slot-reading-footer') || !canvas.includes('reading-static') || !canvas.includes('reading-footer-spacer')) {
  throw new Error('unified reading footer missing');
}
if (!canvas.includes('codeAsSurface') || !canvas.includes('is-code-surface')) {
  throw new Error('code-as-surface display missing');
}
if (canvas.includes('slot-warning')) {
  throw new Error('unresolved warning must be pill badge, not footer text');
}
if (!css.includes('.line-slot-wrap') || !css.includes('width: 4.5rem') || css.includes('max-width: 6.2rem')) {
  throw new Error('slot column width must stay fixed; reading-choice must not widen past pill');
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
