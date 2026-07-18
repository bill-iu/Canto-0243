/** pos-meta + carrier self-check — npx tsx client/scripts/pos-meta-self-check.ts */
import {
  formalPosMap,
  initProjectPosCarrier,
  posDisplayChips,
  resetProjectPosCarrier,
} from '../src/pos/carrier.ts';
import {
  filterCandidatesBySeedPos,
  filterLiteralsBySeedPos,
  samePosBucket,
} from '../src/workbench/pos-meta.ts';

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

assert(samePosBucket(new Set(), new Set(['n'])) === true, 'empty seed keeps');
assert(samePosBucket(new Set(['n']), new Set()) === true, 'unknown cand keeps');
assert(samePosBucket(new Set(['n']), new Set(['n', 'v'])) === true, 'overlap keep');
assert(samePosBucket(new Set(['n']), new Set(['v'])) === false, 'no overlap drop');

const map = new Map<string, Set<string>>([
  ['開心', new Set(['a'])],
  ['快樂', new Set(['a'])],
  ['行走', new Set(['v'])],
  ['道路', new Set(['n'])],
]);
const kept = filterLiteralsBySeedPos('開心', ['快樂', '行走', '道路', '未知'], map);
assert(
  kept.length === 2 && kept.includes('快樂') && kept.includes('未知'),
  `filter got ${kept.join(',')}`,
);

const cands = filterCandidatesBySeedPos(
  '開心',
  [{ literal: '快樂' }, { literal: '行走' }, { literal: '未知' }],
  map,
);
assert(cands.length === 2 && cands[0]!.literal === '快樂', 'candidate filter');

resetProjectPosCarrier();
initProjectPosCarrier({
  version: '0.1.0',
  p0HardGate: false,
  literals: {
    開心: { pos: ['a'] },
    一石二鳥: { pos: ['v'], family: 'idiom' },
    被打: { pos: ['v'], voice: 'passive' },
  },
});
assert(posDisplayChips('開心').join() === '形', 'chip a');
assert(posDisplayChips('一石二鳥').includes('熟語'), 'chip idiom');
assert(posDisplayChips('被打').includes('被動'), 'chip passive');
assert(posDisplayChips('無標').length === 0, 'empty chips');
assert(formalPosMap().get('開心')?.has('a'), 'formal map');
resetProjectPosCarrier();

console.log('pos-meta-self-check: ok');
