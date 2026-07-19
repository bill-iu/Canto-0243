/** Three-axis creator filter contract. */
import { initProjectPosCarrier, resetProjectPosCarrier } from '../src/pos/carrier.ts';
import {
  EMPTY_POS_FILTER,
  literalMatchesPosFilter,
  normalizePosFilter,
  posFilterActiveCount,
  togglePosFilterValue,
} from '../src/pos/filter.ts';

function assert(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}

initProjectPosCarrier({
  version: '1',
  p0HardGate: true,
  literals: {
    成句: { pos: ['v'], trust: 'high', gate: ['v'], show: ['v'], family: 'chengyu', voice: 'active' },
    俗句: { pos: ['n'], trust: 'high', gate: ['n'], show: ['n'], family: 'suyu', voice: 'passive' },
    傘句: { pos: ['a'], trust: 'high', gate: ['a'], show: ['a'], family: 'idiom' },
    中信: { pos: ['v'], trust: 'medium', gate: ['v'] },
  },
});

assert(literalMatchesPosFilter('不存在', EMPTY_POS_FILTER), 'empty filter keeps missing');
let filter = togglePosFilterValue(EMPTY_POS_FILTER, 'pos', 'v');
assert(literalMatchesPosFilter('成句', filter), 'pos v');
assert(!literalMatchesPosFilter('俗句', filter), 'pos rejects n');
assert(!literalMatchesPosFilter('中信', filter), 'creator filter must not use medium gate');
filter = togglePosFilterValue(filter, 'pos', 'n');
assert(literalMatchesPosFilter('成句', filter) && literalMatchesPosFilter('俗句', filter), 'pos OR');
filter = togglePosFilterValue(filter, 'family', 'chengyu');
assert(literalMatchesPosFilter('成句', filter) && !literalMatchesPosFilter('俗句', filter), 'axes AND');
filter = togglePosFilterValue(filter, 'family', 'suyu');
assert(literalMatchesPosFilter('俗句', filter), 'family leaf OR');
filter = togglePosFilterValue(filter, 'family', 'idiom');
assert(filter.family.join() === 'idiom', 'umbrella clears leaves');
assert(
  literalMatchesPosFilter('成句', { ...EMPTY_POS_FILTER, family: ['idiom'] })
    && literalMatchesPosFilter('傘句', { ...EMPTY_POS_FILTER, family: ['idiom'] }),
  'umbrella all family',
);
filter = togglePosFilterValue(filter, 'family', 'chengyu');
assert(filter.family.join() === 'chengyu', 'leaf clears umbrella');
filter = togglePosFilterValue(filter, 'voice', 'passive');
assert(!literalMatchesPosFilter('成句', filter), 'voice AND');
assert(posFilterActiveCount(filter) === 4, 'active chip count');
assert(normalizePosFilter({ pos: ['v', 'v'], family: ['idiom', 'suyu'], voice: [] }).family.join() === 'idiom', 'normalize');
resetProjectPosCarrier();

console.log('pos-filter-self-check: ok');
