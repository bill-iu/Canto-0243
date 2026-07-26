import assert from 'node:assert/strict';

import {
  buildQueryWorkspacePortableUrl,
  createDatabaseQueryWorkspaceAdapter,
  createPortableQueryWorkspaceAdapter,
  decodeQueryWorkspaceHint,
  mapPortableWordRead,
} from '../src/query-workspace/query-engine-adapter.ts';

const request = {
  query: '開心',
  mode: 'synonym' as const,
  limit: 20,
  offset: 0,
  fallback_0243_mode: '394052' as const,
  signal: new AbortController().signal,
};
const url = buildQueryWorkspacePortableUrl(request);
assert.ok(url.includes('mode=syn'));
assert.ok(url.includes('fallback_0243_mode=m3'));
assert.ok(url.includes('q=%E9%96%8B%E5%BF%83'));
assert.equal(decodeQueryWorkspaceHint("UTF-8''%E6%B8%AC"), '測');
assert.deepEqual(mapPortableWordRead({ char: '甲', code: '3', jyutping: 'gaap3' }), {
  word: '甲',
  code: '3',
  jyutping: 'gaap3',
  score: 0,
  resultType: undefined,
  anchor_dimension: undefined,
  relation: undefined,
  in_db: undefined,
  source: undefined,
});

let seenRequest: unknown = null;
const database = createDatabaseQueryWorkspaceAdapter(async (input) => {
  seenRequest = input;
  return { items: [{ word: input.query }], total: 1, hint: undefined };
});
const databasePage = await database.searchPage({
  ...request,
  mode: '0243',
  fallback_0243_mode: undefined,
});
assert.equal((seenRequest as { shouldCancel?: unknown }).shouldCancel instanceof Function, true);
assert.deepEqual(databasePage.items, [{ word: '開心' }]);

const abortDuringLoad = new AbortController();
const abortingDatabase = createDatabaseQueryWorkspaceAdapter(async (input) => {
  abortDuringLoad.abort();
  assert.equal(input.shouldCancel?.(), true);
  return { items: [{ word: '不可提交' }], total: 1, hint: undefined };
});
await assert.rejects(
  abortingDatabase.searchPage({ ...request, mode: '0243', signal: abortDuringLoad.signal }),
  (error: unknown) => error instanceof DOMException && error.name === 'AbortError',
);

let seenSignal: AbortSignal | undefined;
const portable = createPortableQueryWorkspaceAdapter(async (_input, init) => {
  seenSignal = init?.signal as AbortSignal;
  return new Response(JSON.stringify([{ char: '甲', code: '3', jyutping: 'gaap3' }]), {
    headers: { 'X-Search-Total': '1', 'X-Search-Hint': "UTF-8''%E6%B8%AC" },
  });
});
const portablePage = await portable.searchPage({ ...request, mode: '0243' });
assert.equal(seenSignal, request.signal);
assert.equal(portablePage.total, 1);
assert.equal(portablePage.hint, '測');
assert.equal(portablePage.items[0]?.word, '甲');

console.log('query-workspace-adapter self-check ok');
