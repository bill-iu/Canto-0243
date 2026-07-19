import {
  WORKBENCH_INGEST_KEY,
  WORKBENCH_NAVIGATE_KEY,
  WORKBENCH_OPEN_SEARCH_KEY,
  consumeIngest,
  consumeNavigate,
  consumeOpenSearch,
  hasWorkbenchDraft,
  readWorkbenchSelectionWidth,
  writeIngest,
  writeNavigate,
  writeOpenSearch,
} from '../src/workbench/workbench-bridge.ts';
import { createLineDraft, lineDraftReducer } from '../src/workbench/line-draft.ts';
import { parseLineInput } from '../src/workbench/line-input.ts';
import { saveLineDraft } from '../src/workbench/line-draft-storage.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`workbench bridge: ${message}`);
}

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem(key: string) {
      return values.has(key) ? values.get(key)! : null;
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
    removeItem(key: string) {
      values.delete(key);
    },
    raw: values,
  };
}

const storage = memoryStorage();
writeIngest(storage, { literal: '香港', mode: 'replace' });
assert(storage.getItem(WORKBENCH_INGEST_KEY)?.includes('香港'), 'ingest write missing');
const ingest = consumeIngest(storage);
assert(ingest?.literal === '香港' && ingest.mode === 'replace', 'ingest consume failed');
assert(storage.getItem(WORKBENCH_INGEST_KEY) == null, 'ingest key not cleared');

writeOpenSearch(storage, { literal: '香江' });
assert(storage.getItem(WORKBENCH_OPEN_SEARCH_KEY)?.includes('香江'), 'open-search write missing');
const open = consumeOpenSearch(storage);
assert(open?.literal === '香江', 'open-search consume failed');
assert(storage.getItem(WORKBENCH_OPEN_SEARCH_KEY) == null, 'open-search key not cleared');

writeNavigate(storage, { kind: 'mode', family: 'synonym' });
assert(storage.getItem(WORKBENCH_NAVIGATE_KEY)?.includes('synonym'), 'navigate write missing');
const nav = consumeNavigate(storage);
assert(nav?.kind === 'mode' && nav.family === 'synonym', 'navigate mode consume failed');
assert(storage.getItem(WORKBENCH_NAVIGATE_KEY) == null, 'navigate key not cleared');

writeNavigate(storage, { kind: 'guide' });
assert(consumeNavigate(storage)?.kind === 'guide', 'navigate guide failed');
writeNavigate(storage, { kind: 'about' });
assert(consumeNavigate(storage)?.kind === 'about', 'navigate about failed');

storage.setItem(WORKBENCH_NAVIGATE_KEY, JSON.stringify({ version: 1, kind: 'mode', family: 'nope', createdAt: 1 }));
assert(consumeNavigate(storage) == null, 'invalid navigate family accepted');

storage.setItem(WORKBENCH_INGEST_KEY, JSON.stringify({ version: 2, literal: 'x', mode: 'replace', createdAt: 1 }));
assert(consumeIngest(storage) == null, 'unknown ingest version accepted');

storage.setItem(WORKBENCH_INGEST_KEY, JSON.stringify({ version: 1, literal: '', mode: 'replace', createdAt: 1 }));
assert(consumeIngest(storage) == null, 'empty literal accepted');

storage.setItem(WORKBENCH_INGEST_KEY, JSON.stringify({ version: 1, literal: '港', mode: 'merge', createdAt: 1 }));
assert(consumeIngest(storage) == null, 'invalid mode accepted');

const parsed = parseLineInput('我愛香港');
assert(parsed.ok, 'draft fixture');
let draft = createLineDraft(parsed);
draft = lineDraftReducer(draft, { type: 'select', start: 2, width: 2 });
saveLineDraft(storage, draft);
assert(hasWorkbenchDraft(storage), 'hasWorkbenchDraft false for filled draft');
assert(readWorkbenchSelectionWidth(storage) === 2, 'selection width peek failed');

console.log('workbench bridge self-check ok');
