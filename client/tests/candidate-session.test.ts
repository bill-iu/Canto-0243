import assert from 'node:assert/strict';
import test from 'node:test';

import { initProjectPosCarrier, resetProjectPosCarrier } from '../src/pos/carrier.ts';
import { planHasQueryableSlots } from '../src/workbench/code-constraint.ts';
import {
  applyCreatorPosFilter,
  candidateSessionView,
  emptyCandidateSession,
  resetWithPlan,
  runCandidateFetch,
  type CandidatePlanBase,
} from '../src/workbench/candidate-session/index.ts';
import type {
  ReplacementPlanV1,
  WorkbenchCandidateResponse,
} from '../src/workbench/contracts.ts';

function planBase(): CandidatePlanBase {
  return {
    version: 1,
    selectionVersion: 3,
    width: 2,
    mode: 'm1',
    slots: [],
    semanticIntent: 'off',
    semanticSeed: undefined,
  };
}

function page(offset: number): WorkbenchCandidateResponse {
  const rows = Array.from({ length: 400 }, (_, index) => {
    const literal = `w${String(offset + index).padStart(5, '0')}`;
    return {
      literal,
      jyutping: 'gaa1',
      code: '12',
      group: 'sound_only' as const,
      reasons: [{ kind: 'frequency_rank' as const, positions: [] }],
      sourceRank: offset + index,
    };
  });
  return {
    version: 1,
    selectionVersion: 3,
    exact: { direct_syn: [], semantic_related: [], sound_only: rows },
    total: 10000,
    engineTotal: 10000,
    relaxation: null,
  };
}

test('POS-filtered fetch caps automatic probing at five pages', async () => {
  initProjectPosCarrier({
    version: 'test',
    p0HardGate: false,
    literals: { w01600: { pos: ['v'], voice: 'passive' } },
  });
  try {
    const state = resetWithPlan(
      emptyCandidateSession(400),
      planBase(),
      { pos: [], family: [], voice: ['passive'] },
    );
    const calls: ReplacementPlanV1[] = [];
    const result = await runCandidateFetch(state, async (request) => {
      calls.push(request);
      return page(request.offset ?? 0);
    });

    assert.equal(calls.length, 5);
    assert.equal(result.engineCursor, 2000);
    assert.equal(candidateSessionView(result).filteredCount, 1);
    assert.equal(candidateSessionView(result).hasMore, true);
  } finally {
    resetProjectPosCarrier();
  }
});

test('POS-filtered empty page hides relaxation for a non-empty raw pool', () => {
  initProjectPosCarrier({ version: 'test', p0HardGate: false, literals: {} });
  try {
    const response = {
      ...page(0),
      relaxation: {} as never,
    };
    const filtered = applyCreatorPosFilter(response, { pos: [], family: [], voice: ['passive'] });
    assert.equal(filtered.relaxation, null);
  } finally {
    resetProjectPosCarrier();
  }
});

test('an unrestricted width plan remains queryable without a semantic seed', () => {
  assert.equal(planHasQueryableSlots(2, [], '', 'off'), true);
});
