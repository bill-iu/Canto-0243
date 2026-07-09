/** Source contract — node frontend/scripts/search-page-limit-self-check.mjs */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const ctx = readFileSync(join(root, 'frontend/app-context.mjs'), 'utf8');
const q = readFileSync(join(root, 'client/src/db/query.ts'), 'utf8');
const hook = readFileSync(join(root, 'client/src/hooks/useDB.tsx'), 'utf8');
const cancel = readFileSync(join(root, 'client/src/db/search-cancel.ts'), 'utf8');

for (const [label, src] of [
  ['app-context', ctx],
  ['query.ts', q],
]) {
  if (!src.includes('SEARCH_FIRST_PAGE_SIZE = 400')) throw new Error(`${label}: first 400`);
  if (!src.includes('SEARCH_PAGE_SIZE = 800')) throw new Error(`${label}: max 800`);
  if (!src.includes('searchLimitForOffset')) throw new Error(`${label}: searchLimitForOffset`);
}

if (!hook.includes('shouldCancel')) throw new Error('useSearch: shouldCancel');
if (!hook.includes('SEARCH_FIRST_PAGE_SIZE')) throw new Error('useSearch: first page');
// P3: loading visible even with stale results (no early return on results.length)
if (hook.includes('if (results.length > 0)') && hook.includes('setLoadingVisible(false)')) {
  const loadingEffect = hook.slice(hook.indexOf('// P3: show'));
  if (loadingEffect.includes('if (results.length > 0)')) {
    throw new Error('useSearch: must not hide loading when stale results exist');
  }
}
if (!cancel.includes('SearchCancelledError')) throw new Error('search-cancel missing');
if (!cancel.includes('throwIfSearchCancelled')) throw new Error('throwIf missing');

// F2: new search always offset 0; do not cache empty pages
const workbench = readFileSync(join(root, 'frontend/search-workbench.mjs'), 'utf8');
if (!workbench.includes('const offset = isLoadMore ? tab.offset || 0 : 0')) {
  throw new Error('searchDict: new search must force offset 0');
}
if (!workbench.includes('!isLoadMore && data.length > 0')) {
  throw new Error('searchDict: must only cache non-empty first pages');
}
if (workbench.includes('if (cached.data.length === 0) {\n        $.results.innerHTML = emptySearchResultsHtml')) {
  throw new Error('searchDict: must not trust empty cache entries');
}

console.log('search-page-limit-self-check: ok');
