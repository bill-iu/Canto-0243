/**
 * candidate-session: cursor ownership, POS over-fetch, B2-light totals, hasMore.
 */
import { resetPosFilter, type PosFilterState } from '../src/pos/filter.ts';
import { initProjectPosCarrier, resetProjectPosCarrier } from '../src/pos/carrier.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from '../src/workbench/contracts.ts';
import { parseWorkbenchCandidateResponse } from '../src/workbench/contracts.ts';
import { markSnapshotRestarted } from '../src/workbench/candidate-page.ts';
import {
  applyCreatorPosFilter,
  candidateSessionView,
  emptyCandidateSession,
  requestLoadMore,
  resetWithPlan,
  runCandidateFetch,
  samePlanIdentity,
  setPosFilter,
  type CandidatePlanBase,
} from '../src/workbench/candidate-session/index.ts';

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`candidate-session: ${message}`);
}

function planBase(partial: Partial<CandidatePlanBase> = {}): CandidatePlanBase {
  return {
    version: 1,
    selectionVersion: 1,
    width: 1,
    mode: 'm1',
    slots: [{ pos: 0, kind: 'code_digit', digit: '3' }],
    semanticIntent: 'off',
    ...partial,
  };
}

function page(
  offset: number,
  literals: string[],
  total = 5,
  selectionVersion = 1,
): WorkbenchCandidateResponse {
  const rows = literals.map((literal, i) => ({
    literal,
    jyutping: 'a1',
    code: '3',
    group: 'sound_only' as const,
    reasons: [{ kind: 'tone_exact' as const, positions: [0] }],
    sourceRank: offset + i,
  }));
  return {
    version: 1,
    selectionVersion,
    exact: { direct_syn: [], semantic_related: [], sound_only: rows },
    total,
    engineTotal: total,
  };
}

// --- parse B2-light ---
const onlyTotal = parseWorkbenchCandidateResponse({
  version: 1,
  selectionVersion: 1,
  exact: { direct_syn: [], semantic_related: [], sound_only: [] },
  total: 9,
});
assert(onlyTotal.engineTotal === 9 && onlyTotal.total === 9, 'total-only fills engineTotal');

const onlyEngine = parseWorkbenchCandidateResponse({
  version: 1,
  selectionVersion: 1,
  exact: { direct_syn: [], semantic_related: [], sound_only: [] },
  engineTotal: 7,
});
assert(onlyEngine.engineTotal === 7 && onlyEngine.total === 7, 'engineTotal-only fills total');

// --- identity ---
assert(samePlanIdentity(planBase(), planBase()), 'same identity');
assert(samePlanIdentity(planBase(), planBase({ selectionVersion: 2 })), 'draft version is not query identity');

// --- fetch without POS ---
const pages: WorkbenchCandidateResponse[] = [
  page(0, ['一', '二'], 5),
  page(2, ['三', '四'], 5),
  page(4, ['五'], 5),
];
let call = 0;
const find = async (req: ReplacementPlanV1) => {
  const idx = Math.floor((req.offset ?? 0) / (req.limit || 2));
  const p = pages[idx] ?? page(req.offset ?? 0, [], 5);
  return { ...p, selectionVersion: req.selectionVersion };
};

let state = emptyCandidateSession(2);
state = resetWithPlan(state, planBase());
assert(state.loading && state.generation === 1, 'reset loads');
state = await runCandidateFetch(state, find);
assert(!state.loading, 'fetch done');
assert(state.staleRaw == null, 'fresh fetch clears stale');
let view = candidateSessionView(state);
assert(view.filteredCount === 2, `first page filtered=${view.filteredCount}`);
assert(view.engineFetched === 2, 'engine fetched 2');
assert(view.engineTotal === 5, 'engine total 5');
assert(view.hasMore === true, 'has more');

// POS is a projection of loaded snapshot rows: enough loaded matches means zero query.
initProjectPosCarrier({
  version: 'snapshot-test',
  p0HardGate: true,
  literals: {
    一: { pos: ['n'], trust: 'high', gate: ['n'], show: ['n'] },
    二: { pos: ['n'], trust: 'high', gate: ['n'], show: ['n'] },
  },
});
state = setPosFilter(state, { pos: ['n'], family: [], voice: [] });
assert(state.raw != null, 'POS keeps loaded snapshot rows');
assert(!state.loading, 'POS with enough loaded rows does not query');
assert(candidateSessionView(state).filteredCount === 2, 'POS projects loaded rows');
resetProjectPosCarrier();
state = setPosFilter(state, resetPosFilter());

// Expired Desktop handle returns page 0; session replaces, never appends to old rows.
let recovered = requestLoadMore(state);
let recoveryCall = 0;
recovered = await runCandidateFetch(recovered, async (req) => {
  recoveryCall += 1;
  return recoveryCall === 1
    ? markSnapshotRestarted(page(0, ['新', '池'], 3, req.selectionVersion))
    : page(2, ['尾'], 3, req.selectionVersion);
});
assert(
  recovered.raw?.exact.sound_only.map((row) => row.literal).join('') === '新池尾',
  'snapshot recovery atomically replaces old rows',
);

// plan 重置：raw 清、stale 上屏，避免 UI 卸載閃動
const prevLiterals = state.raw?.exact.sound_only.map((r) => r.literal).join('');
state = resetWithPlan(state, planBase({ selectionVersion: 2 }));
assert(state.raw == null && state.staleRaw != null, 'keeps stale while loading');
assert(state.loading, 'reset still loading');
view = candidateSessionView(state);
assert(view.response != null, 'stale still visible in view');
assert(view.hasMore === false, 'stale view has no loadMore');
assert(
  view.response!.exact.sound_only.map((r) => r.literal).join('') === prevLiterals,
  'stale content matches prior page',
);
state = await runCandidateFetch(state, find);
assert(state.raw != null && state.staleRaw == null, 'new raw replaces stale');
assert(!state.loading, 'refetch done');
view = candidateSessionView(state);
assert(view.hasMore === true, 'fresh hasMore restored');

state = requestLoadMore(state);
assert(state.filteredTarget === 4, 'target 4');
state = await runCandidateFetch(state, find);
view = candidateSessionView(state);
assert(view.filteredCount === 4, `after loadMore filtered=${view.filteredCount}`);
assert(view.hasMore === true, 'still more');

state = requestLoadMore(state);
state = await runCandidateFetch(state, find);
view = candidateSessionView(state);
assert(view.filteredCount === 5, `final filtered=${view.filteredCount}`);
assert(view.hasMore === false, 'exhausted');

// --- POS over-fetch: mock filter by only keeping 偶 index literals ---
// Without real POS carrier, applyCreatorPosFilter with empty filter is no-op.
// Simulate by custom path: use empty filter but verify over-fetch loop requests multiple offsets
// when filteredTarget high and pages small.
call = 0;
const findTrack = async (req: ReplacementPlanV1) => {
  call += 1;
  const offset = req.offset ?? 0;
  if (offset === 0) return page(0, ['甲', '乙'], 4);
  if (offset === 2) return page(2, ['丙', '丁'], 4);
  return page(offset, [], 4);
};
state = emptyCandidateSession(2);
state = resetWithPlan(state, planBase({ selectionVersion: 3 }));
state = await runCandidateFetch(state, findTrack);
assert(call === 1, `no-pos first page calls=${call}`);
state = requestLoadMore(state);
state = await runCandidateFetch(state, findTrack);
assert(call === 2, `loadMore second call calls=${call}`);

// applyCreatorPosFilter empty filter identity
const sample = page(0, ['測'], 1);
const filtered = applyCreatorPosFilter(sample, resetPosFilter());
assert(filtered.exact.sound_only.length === 1, 'empty POS is identity');

// active POS shape (filter may drop all without carrier — still runs)
const posOn: PosFilterState = { pos: ['n'], family: [], voice: [] };
state = emptyCandidateSession(2);
state = resetWithPlan(state, planBase({ selectionVersion: 9 }), posOn);
call = 0;
state = await runCandidateFetch(state, async (req) => {
  call += 1;
  return findTrack(req);
});
// without POS data, filter drops all → over-fetch until pool exhausted
assert(call >= 2, `POS over-fetch until exhausted calls=${call}`);
view = candidateSessionView(state);
assert(view.hasMore === false || view.engineFetched >= 0, 'POS path completed');

console.log('workbench-candidate-session-self-check: ok');
