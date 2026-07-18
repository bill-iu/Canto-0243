import fs from 'node:fs';

const bridge = fs.readFileSync('src/workbench/workbench-bridge.ts', 'utf8');
const page = fs.readFileSync('src/workbench/WorkbenchPage.tsx', 'utf8');
const app = fs.readFileSync('src/App.tsx', 'utf8');
const modal = fs.readFileSync('src/workbench/PutInWorkbenchModal.tsx', 'utf8');
const compare = fs.readFileSync('src/workbench/ComparePanel.tsx', 'utf8');

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench bridge ui: ${message}`);
}

assert(bridge.includes('canto-workbench-ingest-v1'), 'ingest key missing');
assert(bridge.includes('canto-workbench-open-search-v1'), 'open-search key missing');
assert(page.includes('consumeIngest(sessionStorage)'), 'workbench must consume ingest once');
assert(!/consumeIngest[\s\S]{0,400}apply_candidate/.test(page), 'ingest must not auto-apply candidates');
assert(app.includes('openSearchTabWithQuery'), 'search open must use new query tab API');
assert(app.includes('consumeOpenSearch(sessionStorage)'), 'search must consume open-search payload');
assert(app.includes('PutInWorkbenchModal'), 'put confirmation modal missing');
assert(modal.includes('取代整句') && modal.includes('插入到已鎖範圍'), 'modal actions missing');
assert(modal.includes('字數不符') || modal.includes('已鎖範圍是'), 'insert width guard copy missing');
assert(compare.includes('在搜尋頁查看'), 'compare open-in-search missing');

console.log('workbench bridge UI self-check ok');
