/**
 * P3#5: dispatch is thin; executors hold route implementation.
 */
import fs from 'node:fs';

const dispatch = fs.readFileSync('src/db/query/dispatch.ts', 'utf8');
const word = fs.readFileSync('src/db/query/word-lookup-executor.ts', 'utf8');
const relation = fs.readFileSync('src/db/query/relation-syntax-executor.ts', 'utf8');
const mask = fs.readFileSync('src/db/query/mask-family-executor.ts', 'utf8');

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`query-dispatch-layout: ${message}`);
}

const dispatchLines = dispatch.split('\n').length;
assert(dispatchLines <= 130, `dispatch.ts too fat (${dispatchLines} lines; want ≤130)`);

assert(dispatch.includes('executeDigitCodeQuery'), 'dispatch must delegate digit');
assert(dispatch.includes('executeWordLookup'), 'dispatch must delegate word lookup');
assert(dispatch.includes('executeRelationLookup'), 'dispatch must delegate relation');
assert(dispatch.includes('executeMaskFamilySearchResult'), 'dispatch must delegate mask');
assert(dispatch.includes('from \'./word-lookup-executor.ts\''), 'import word-lookup-executor');
assert(dispatch.includes('from \'./relation-syntax-executor.ts\''), 'import relation-syntax-executor');
assert(dispatch.includes('from \'./mask-family-executor.ts\''), 'import mask-family-executor');

// Heavy SQL / match work lives in executors, not thin dispatch (list filter SQL is OK)
assert(word.includes('SELECT char, jyutping, code'), 'digit/lookup SQL in word-lookup-executor');
assert(mask.includes('normalizeToMatchSpec'), 'mask uses MatchSpec');
assert(relation.includes('relationLookupItems'), 'relation uses pool projection');

// dispatch should not still define executeWordLookup body
assert(!dispatch.includes('composeTransientWordRows'), 'word lookup body left dispatch');
assert(!dispatch.includes('normalizeToMatchSpec'), 'mask body left dispatch');
assert(!dispatch.includes('relationLookupItems'), 'relation body left dispatch');

console.log('query-dispatch-layout-self-check: ok');
