import fs from 'node:fs';

const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const canvas = fs.readFileSync('src/workbench/SentenceCanvas.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');
const cards = fs.readFileSync('src/workbench/CandidateGrid.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const seams = fs.readFileSync('../tests/smoke/test_workbench_client_seams.py', 'utf8');

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench a11y: ${message}`);
}

assert(page.includes('aria-live="polite"'), 'status regions need aria-live');
assert(canvas.includes('aria-label={`第 ${pos + 1} 個字'), 'slots need accessible labels');
assert(canvas.includes("event.key === 'ArrowLeft'") && canvas.includes('event.shiftKey'), 'keyboard selection missing');
assert(canvas.includes("event.key === ' '"), 'space lock missing');
assert(compare.includes('headingRef.current?.focus()'), 'compare panel must move focus on open');
assert(compare.includes("event.key === 'Escape'"), 'compare panel must close on Escape');
assert(page.includes('previewOrigin.current?.focus()'), 'closing compare must restore focus');
assert(page.includes('[data-line-slot=') && page.includes('.focus()'), 'apply must return focus to slot');
assert(cards.includes('aria-labelledby="candidateHeading"'), 'candidate region needs heading');
assert(css.includes('bottom: 0') && css.includes('compare-panel'), 'narrow compare drawer missing');
assert(!css.includes('writing-mode: vertical'), 'vertical writing mode is forbidden');
assert(seams.includes('writing-mode: horizontal-tb'), 'seam test must guard horizontal layout');
assert(page.includes('尚未圈選字位'), 'empty selection must announce waiting state');
assert(cards.includes('放寬後結果'), 'relaxed results must not stay labelled as exact');

console.log('workbench accessibility self-check ok');
