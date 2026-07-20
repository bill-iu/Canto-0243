import fs from 'node:fs';

const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const cards = fs.readFileSync('src/workbench/CandidateGrid.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');
const canvas = fs.readFileSync('src/workbench/SentenceCanvas.tsx', 'utf8');
const constraints = fs.readFileSync('src/workbench/ConstraintBar.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const app = fs.readFileSync('src/App.tsx', 'utf8');
const detail = fs.readFileSync('src/entry-detail/EntryDetailPanel.tsx', 'utf8');
const lineInputCopy = fs.readFileSync('src/workbench/line-input-copy.ts', 'utf8');
const introCopy = fs.readFileSync('src/workbench/intro-copy.ts', 'utf8');

/** Locked: label + placeholder must stay this exact string (product decision). */
const LOCKED_LINE_INPUT_COPY = '歌詞/0243 碼/漢字加數字混合';
if (!lineInputCopy.includes(`'${LOCKED_LINE_INPUT_COPY}'`)) {
  throw new Error(`line-input-copy must lock WORKBENCH_LINE_INPUT_COPY to ${LOCKED_LINE_INPUT_COPY}`);
}
if (!page.includes('WORKBENCH_LINE_INPUT_COPY')) {
  throw new Error('WorkbenchPage must use WORKBENCH_LINE_INPUT_COPY for placeholder');
}
// Visible label above the line input is removed; copy stays as placeholder + sr-only.
if (!page.includes('className="sr-only"') || !page.includes('htmlFor="lineInput"')) {
  throw new Error('workbench line input must keep sr-only label (no visible label above field)');
}
if (page.includes('原句、394052') || page.includes('例如：香港／39／平仄')) {
  throw new Error('legacy workbench line-input label/placeholder must be removed');
}
if (!page.includes('lexiconVersion={lexiconVersion}')) {
  throw new Error('workbench ModeMenu must show lexicon meta under the menu');
}

// Intro: stacked titles + left-aligned form (grill 2026-07-21)
for (const s of ['創作由你主導', '授漁·句格工作台', '一行拆解，萬種可能', 'VerseCraft Workbench']) {
  if (!introCopy.includes(s)) throw new Error(`intro-copy missing locked string: ${s}`);
}
if (!page.includes('workbenchIntroCopy') || !page.includes('workbench-intro__titles')) {
  throw new Error('WorkbenchPage must use intro-copy for stacked titles');
}
if (page.includes('創作主導權在你手上') || page.includes('不會替你自動填詞') || page.includes('把一句拆開')) {
  throw new Error('legacy workbench intro copy must be removed');
}
if (!css.includes('max-width: 40rem') || !css.includes('align-items: flex-start')) {
  throw new Error('workbench-intro must left-align with form max-width 40rem');
}
if (css.includes('grid-template-columns: minmax(15rem, .8fr)')) {
  throw new Error('wide two-column workbench-intro grid must be removed');
}

for (const group of ['direct_syn', 'semantic_related', 'sound_only']) {
  if (!cards.includes(group)) throw new Error(`missing candidate group ${group}`);
}
if (!compare.includes('套用這個選擇') || !page.includes("type: 'apply_candidate'")) {
  throw new Error('candidate apply is not explicit');
}
if (!compare.includes('posDisplayChips') || !compare.includes('詞性')) {
  throw new Error('compare panel must show project POS chips when present');
}
if (!compare.includes('在搜尋頁查看') || !compare.includes('onOpenInSearch')) {
  throw new Error('open-in-search missing from compare panel');
}
if (!page.includes('不會自動填入字面')) {
  throw new Error('product boundary copy missing (no auto-fill surfaces)');
}
if (!page.includes('WORKBENCH_CANDIDATE_PAGE_SIZE')) {
  throw new Error('candidate page size constant missing from WorkbenchPage');
}
if (!css.includes('.candidate-load-more button') || !css.includes('min-width: min(100%, 16rem)')) {
  throw new Error('load-more must look like a primary button');
}
if (page.includes('limit: 120')) throw new Error('legacy candidate limit 120 must be removed');
if (page.includes("type: 'select', start: 0, width: 1")) {
  throw new Error('creating a line must not auto-select slots');
}
if (!page.includes('consumeIngest') || !page.includes('writeOpenSearch')) {
  throw new Error('workbench bridge consume/write missing');
}
if (!page.includes('hydrateDraftCodes') || !page.includes('pendingResolve')) {
  throw new Error('code hydrate / reading retry missing');
}
if (!page.includes('toggleLockKeepingSpan') || !constraints.includes('空白鍵鎖定')) {
  throw new Error('click-span lock / shortcut hint missing');
}
if (!canvas.includes('點擊鎖定，雙擊改字')) {
  throw new Error('sentence canvas heading copy locked');
}
if (canvas.includes('點擊標定替換段')) {
  throw new Error('legacy canvas mark copy must be removed');
}
if (!css.includes('white-space: nowrap') || !css.includes('.canvas-clear-surfaces')) {
  throw new Error('清空 button must stay horizontal (nowrap)');
}
if (!css.includes('line-input-form__row') || !css.includes('grid-template-columns: minmax(0, 1fr) max-content')) {
  throw new Error('line-input must use single-row grid (input | submit)');
}
if (!page.includes('line-input-form__row') || !page.includes('line-input-form__submit')) {
  throw new Error('WorkbenchPage must mark line-input row/submit classes');
}
if (css.includes('.line-input-form > div { align-items: stretch; flex-direction: column')) {
  throw new Error('narrow line-input must not stack submit under input');
}
if (!css.includes('.workbench-intro__titles .eyebrow') || !css.includes('clamp(1.85rem')) {
  throw new Error('intro type scale h1 > h2 > eyebrow serif missing');
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
if (!cards.includes('池內') || !cards.includes('onLoadMore')) {
  throw new Error('candidate count / load-more wiring missing');
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
if (!canvas.includes('onDoubleClick') || !canvas.includes('line-slot-edit') || !canvas.includes('span-hand-input')) {
  throw new Error('manual cell/span edit UI missing');
}
if (!canvas.includes('onClearSurfaces') || !canvas.includes('canvas-clear-surfaces') || !canvas.includes('清空')) {
  throw new Error('clear-surfaces control missing on sentence canvas');
}
if (!page.includes('clearLineDraft') || !page.includes('clearedUndo') || !page.includes('aria-label="復原清空前的句稿"')) {
  throw new Error('clear-to-empty-workbench undo wiring missing');
}
if (!/建立句格[\s\S]{0,400}aria-label="復原清空前的句稿"[\s\S]{0,120}復原/.test(page)) {
  throw new Error('cleared-draft undo must be a small 復原 button beside line start');
}
if (!constraints.includes('跟原韻') || !constraints.includes('跟原聲') || !constraints.includes('phoneme-dim__ref')) {
  throw new Error('phoneme ref inputs missing');
}
if (!page.includes('WILDCARD_SURFACE') && !page.includes('isHanSurface')) {
  throw new Error('wildcard helpers missing from workbench page');
}
if (page.includes('復原最近一次套用／放寬</button>')) {
  throw new Error('legacy candidate-area undo button must be removed');
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
