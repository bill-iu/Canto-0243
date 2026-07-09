/**
 * PR-B self-check: first-page 400 / max 1200 + cancel helpers.
 * Run: npx tsx client/scripts/search-page-limit-self-check.ts
 */
import assert from 'node:assert/strict';
import {
  SEARCH_FIRST_PAGE_SIZE,
  SEARCH_PAGE_SIZE,
  searchLimitForOffset,
  searchPageSizeForMode,
} from '../src/db/query.ts';
import {
  SearchCancelledError,
  isSearchCancelledError,
  throwIfSearchCancelled,
} from '../src/db/search-cancel.ts';

assert.equal(SEARCH_FIRST_PAGE_SIZE, 400);
assert.equal(SEARCH_PAGE_SIZE, 1200);
assert.equal(searchLimitForOffset('0243', 0), 400);
assert.equal(searchLimitForOffset('02493', 0), 400);
assert.equal(searchLimitForOffset('394052', 0), 400);
assert.equal(searchLimitForOffset('0243', 400), 1200);
assert.equal(searchLimitForOffset('synonym', 0), 400);
assert.equal(searchPageSizeForMode('0243'), 1200);

let hit = false;
try {
  throwIfSearchCancelled(() => true);
} catch (e) {
  hit = isSearchCancelledError(e);
  assert.ok(e instanceof SearchCancelledError);
}
assert.equal(hit, true);
throwIfSearchCancelled(() => false);
throwIfSearchCancelled(undefined);

console.log('search-page-limit-self-check: ok');
