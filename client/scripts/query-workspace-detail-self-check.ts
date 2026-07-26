import assert from 'node:assert/strict';

import {
  createMemoryQueryWorkspaceDetailAdapter,
  type QueryWorkspaceDetailStage,
} from '../src/query-workspace/detail-adapter.ts';
import type { EntryDetailModel } from '../src/entry-detail/types.ts';

const model = (literal: string, syns: string[] = [], ants: string[] = []): EntryDetailModel => ({
  literal,
  length: [...literal].length,
  corpusWeight: 1,
  readings: [],
  sources: [],
  syns,
  ants,
});

const stages: QueryWorkspaceDetailStage[] = [];
let coreCalls = 0;
let mergeWaited = false;
const adapter = createMemoryQueryWorkspaceDetailAdapter({
  core: async (literal) => {
    coreCalls += 1;
    return model(literal);
  },
  hasRelations: async () => true,
  enrichDb: async (value) => ({ ...value, corpusWeight: 2 }),
  enrichRelations: async (value) => ({ ...value, syns: ['朋'], ants: ['敵'] }),
});

const loaded = await adapter.load('友', undefined, {
  waitForPickMerge: async () => {
    mergeWaited = true;
  },
  onStage: (stage) => stages.push(stage),
});
assert.deepEqual(loaded?.syns, ['朋']);
assert.deepEqual(loaded?.ants, ['敵']);
assert.equal(loaded?.corpusWeight, 2);
assert.equal(coreCalls, 1);
assert.equal(mergeWaited, true);
assert.deepEqual(stages.map((stage) => stage.kind), ['core', 'relations-start']);

const seeded = await adapter.load('友', model('友'), { onStage: (stage) => stages.push(stage) });
assert.equal(coreCalls, 1, 'seeded load should not hit the core source');
assert.equal(seeded?.literal, '友');

const controller = new AbortController();
controller.abort();
await assert.rejects(
  () => adapter.load('友', undefined, { signal: controller.signal }),
  (error: unknown) => error instanceof DOMException && error.name === 'AbortError',
);

console.log('query-workspace-detail self-check ok');
