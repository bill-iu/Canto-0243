import fs from 'node:fs';

const engine = fs.readFileSync('src/db/position-match/engine.ts', 'utf8');
const constraints = fs.readFileSync('src/workbench/ConstraintBar.tsx', 'utf8');
const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const css = fs.readFileSync('src/workbench/workbench-page.css', 'utf8');
const entry = fs.readFileSync('src/pwa-app.css', 'utf8');
const app = fs.readFileSync('src/App.tsx', 'utf8');
const bridge = fs.readFileSync('src/workbench/workbench-bridge.ts', 'utf8');

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
if (!constraints.includes('整段押韻') || !constraints.includes('phoneme-dim')) {
  throw new Error('phoneme dimension checklist missing');
}
if (constraints.includes('finalAnchorDisabled') || constraints.includes('末格同韻')) {
  throw new Error('legacy final/initial anchor buttons must be gone');
}
if (page.includes('返回查韻') || page.includes('workbench-brand') || page.includes('back-search')) {
  throw new Error('legacy back-to-search chrome must be removed');
}
if (!page.includes('ModeMenu') || !page.includes('HeaderHero') || !page.includes('BrandLogo')) {
  throw new Error('workbench header must reuse search chrome');
}
if (!page.includes('mode="0243"') || page.includes('onOpenWorkbench')) {
  throw new Error('workbench ModeMenu must default 0243 and omit workbench entry');
}
if (!page.includes('workbench-route') || !css.includes('body.query-tabs-app.workbench-route')) {
  throw new Error('workbench must unlock document scroll');
}
if (!css.includes('font-family: inherit')) {
  throw new Error('workbench fonts must inherit search shell');
}
if (!bridge.includes('WORKBENCH_NAVIGATE_KEY') || !bridge.includes('writeNavigate') || !bridge.includes('consumeNavigate')) {
  throw new Error('navigate bridge missing');
}
if (!app.includes('consumeNavigate') || !app.includes("nav?.kind === 'guide'")) {
  throw new Error('App must consume workbench navigate intents');
}

console.log('workbench polish self-check ok');
