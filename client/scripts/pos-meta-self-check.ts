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
  p0HardGate: true,
  literals: {
    開心: { pos: ['a'], trust: 'high', gate: ['a'], show: ['a'] },
    一石二鳥: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], family: 'idiom' },
    畫蛇添足: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], family: 'chengyu' },
    牙斬斬: { pos: ['a'], trust: 'high', gate: ['a'], show: ['a'], family: 'suyu' },
    三歲定八十: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], family: 'yanyu' },
    牛皮燈籠: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], family: 'xiehouyu' },
    被打: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], voice: 'passive' },
    // cow-single draft: raw pos present but no gate/show
    草稿: { pos: ['n'], trust: 'low' },
    // cow-multi: gate yes, show no
    雙標: { pos: ['n', 'v'], trust: 'medium', gate: ['n', 'v'] },
  },
});
assert(posDisplayChips('開心').join() === '形', 'chip a');
assert(posDisplayChips('一石二鳥').includes('熟語'), 'chip idiom');
assert(posDisplayChips('畫蛇添足').includes('成語'), 'chip chengyu');
assert(posDisplayChips('牙斬斬').includes('俗語'), 'chip suyu');
assert(posDisplayChips('三歲定八十').includes('諺語'), 'chip yanyu');
assert(posDisplayChips('牛皮燈籠').includes('歇後語'), 'chip xiehouyu');
assert(posDisplayChips('被打').includes('被動'), 'chip passive');
// Grill C: display chips use show ∪ pos (any trust); no 「未審」 label
assert(posDisplayChips('草稿').join() === '名', 'low trust shows formal pos chip');
assert(posDisplayChips('雙標').includes('名') && posDisplayChips('雙標').includes('動'), 'medium shows pos chips');
assert(posDisplayChips('無標').length === 0, 'empty chips');
assert(formalPosMap().get('開心')?.has('a'), 'formal map high');
assert(formalPosMap().get('雙標')?.has('v'), 'gate includes medium');
assert(!formalPosMap().has('草稿'), 'low trust not in gate map (seed/gate path)');
resetProjectPosCarrier();

console.log('pos-meta-self-check: ok');
