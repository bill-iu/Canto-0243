import fs from 'node:fs';

const engine = fs.readFileSync('src/db/position-match/engine.ts', 'utf8');
const constraints = fs.readFileSync('src/workbench/ConstraintBar.tsx', 'utf8');
const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const entry = fs.readFileSync('src/pwa-app.css', 'utf8');

if (engine.includes('const phonemeSlot = !code ? firstPhonemeAnchorSlot(spec) : null')) {
  throw new Error('dense code must not skip phoneme anchors');
}
if (!engine.includes('Prefer phoneme index whenever anchors exist')) {
  throw new Error('phoneme-anchor preference comment missing');
}
if (!constraints.includes('value="m1">0243</option>') || !constraints.includes('value="m2">02493</option>')) {
  throw new Error('tone profile must show 0243 as m1');
}
if (!constraints.includes('value="m3">394052</option>')) {
  throw new Error('tone profile labels missing');
}
if (!page.includes("useState<ReplacementPlanV1['mode']>('m1')")) {
  throw new Error('default tone mode must be m1 / 0243');
}
if (css.includes('--wb-ink') || css.includes('#f4efe7') || css.includes('#a83f2d')) {
  throw new Error('workbench page still uses private palette tokens');
}
if (!css.includes('var(--ink)') || !css.includes('var(--surface)') || !css.includes('var(--accent)')) {
  throw new Error('workbench page must use shared design tokens');
}
if (!entry.includes('.workbench-entry:hover') || !entry.includes('var(--accent-strong)')) {
  throw new Error('workbench entry button must share accent tokens');
}
if (!constraints.includes('finalAnchorDisabled') || !constraints.includes('initialAnchorDisabled')) {
  throw new Error('anchor buttons need per-end disable flags');
}

console.log('workbench polish self-check ok');
