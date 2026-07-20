import fs from 'node:fs';

const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const canvas = fs.readFileSync('src/workbench/SentenceCanvas.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');
const cards = fs.readFileSync('src/workbench/CandidateGrid.tsx', 'utf8');
const constraints = fs.readFileSync('src/workbench/ConstraintBar.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const seams = fs.readFileSync('../tests/smoke/test_workbench_client_seams.py', 'utf8');

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench a11y: ${message}`);
}

assert(page.includes('aria-live="polite"'), 'status regions need aria-live');
assert(canvas.includes('aria-label={`第 ${pos + 1} 個字'), 'slots need accessible labels');
assert(canvas.includes("event.key === 'ArrowLeft'") && canvas.includes("event.key === 'ArrowRight'"), 'keyboard focus move missing');
assert(canvas.includes("event.key === ' '"), 'space span-mark missing');
assert(!page.includes("event.key === 'l'") && !page.includes("event.key === 'L'"), 'legacy L batch-lock must be removed');
assert(page.includes('Ctrl') || page.includes('ctrlKey'), 'undo shortcut missing');
assert(constraints.includes('空白鍵鎖定'), 'shortcut hint must mention space lock');
assert(constraints.includes('onUndo') && constraints.includes('復原最近一次套用／放寬／手改'), 'undo must sit in constraint bar');
assert(canvas.includes('onDoubleClick') && canvas.includes('span-hand-input'), 'manual edit surfaces missing');
assert(canvas.includes('span-hand-toggle') && canvas.includes('disabled={!span}'), '✎ toggle must disable without span');
assert(compare.includes('headingRef.current?.focus()'), 'compare panel must move focus on open');
assert(compare.includes("event.key === 'Escape'"), 'compare panel must close on Escape');
assert(page.includes('previewOrigin.current?.focus()'), 'closing compare must restore focus');
assert(page.includes('[data-line-slot=') && page.includes('.focus()'), 'apply must return focus to slot');
assert(cards.includes('aria-labelledby="candidateHeading"'), 'candidate region needs heading');
assert(cards.includes('tabIndex={-1}'), 'candidate group headings must be focusable');
assert(constraints.includes('捷徑：'), 'shortcut hint missing');
assert(constraints.includes('value="m1">0243</option>') && page.includes("('m1')"), 'tone profile 0243 default missing');
assert(css.includes('bottom: 0') && css.includes('compare-panel'), 'narrow compare drawer missing');
assert(!css.includes('writing-mode: vertical'), 'vertical writing mode is forbidden');
assert(seams.includes('writing-mode: horizontal-tb'), 'seam test must guard horizontal layout');
assert(canvas.includes('line-slot__warn') || canvas.includes('讀音未收錄'), 'unresolved must stay announced');
assert(canvas.includes('slot-reading-footer'), 'reading footer row required for equal height');
assert(!canvas.includes('className="slot-warning"'), 'unresolved must not use footer warning text');
assert(page.includes('尚未鎖定替換段'), 'empty span must announce waiting state');
assert(!page.includes('slot.locked && slot.surface'), 'lock must not emit literal_char');

console.log('workbench accessibility self-check ok');
