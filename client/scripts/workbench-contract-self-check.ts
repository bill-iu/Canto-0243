import {
  parseReplacementPlanV1,
  parseWorkbenchCandidateResponse,
} from '../src/workbench/contracts.ts';

let rejected = false;
try {
  parseReplacementPlanV1({
    version: 2,
    selectionVersion: 1,
    width: 1,
    mode: 'm1',
    slots: [],
    semanticIntent: 'off',
    limit: 20,
  });
} catch {
  rejected = true;
}

if (!rejected) {
  throw new Error('workbench contract: unknown version was accepted');
}

rejected = false;
try {
  parseWorkbenchCandidateResponse({
    version: 1,
    selectionVersion: 1,
    exact: {
      direct_syn: [{ literal: '快樂', jyutping: 'faai3 lok6', code: '42', group: 'direct_syn', reasons: ['直接近義'], sourceRank: 1 }],
      semantic_related: [],
      sound_only: [],
    },
    relaxation: null,
  });
} catch {
  rejected = true;
}

if (!rejected) {
  throw new Error('workbench contract: rendered reason string was accepted');
}

const relaxed = parseWorkbenchCandidateResponse({
  version: 1,
  selectionVersion: 8,
  exact: { direct_syn: [], semantic_related: [], sound_only: [] },
  total: 0,
  relaxation: {
    id: 'mode:m3:m2',
    kind: 'loosen_mode',
    from: 'm3',
    to: 'm2',
    candidateCount: 4,
    plan: {
      version: 1,
      selectionVersion: 8,
      width: 1,
      mode: 'm2',
      slots: [{ pos: 0, kind: 'code_digit', digit: '1' }],
      semanticIntent: 'off',
      limit: 20,
      offset: 0,
    },
  },
});

if (relaxed.relaxation?.kind !== 'loosen_mode') {
  throw new Error('workbench contract: relaxation was not parsed');
}

rejected = false;
try {
  parseReplacementPlanV1({
    version: 1,
    selectionVersion: 1,
    width: 1,
    mode: 'm1',
    slots: [{ pos: 0, kind: 'code_digit', digit: '3' }],
    semanticIntent: 'off',
    limit: 401,
  });
} catch {
  rejected = true;
}
if (!rejected) throw new Error('workbench contract: limit > 400 was accepted');

const page = parseReplacementPlanV1({
  version: 1,
  selectionVersion: 1,
  width: 1,
  mode: 'm1',
  slots: [{ pos: 0, kind: 'code_digit', digit: '3' }],
  semanticIntent: 'off',
  limit: 400,
  offset: 400,
});
if (page.offset !== 400) throw new Error('workbench contract: offset not parsed');

console.log('workbench contract self-check ok');
