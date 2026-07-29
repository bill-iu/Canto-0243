import { emptyPhonemeDimPicks } from '../replacement-span.ts';
import type { ConstraintsUI, WorkbenchSession } from './types.ts';

export function defaultConstraintsUI(): ConstraintsUI {
  return {
    mode: 'm1',
    semanticIntent: 'ranked',
    codeConstraint: 'same_tone',
    explicitCode: '',
    rhymeProfile: 'exact',
    rhymePicks: emptyPhonemeDimPicks(),
    initialPicks: emptyPhonemeDimPicks(),
    rhymeRef: '',
    initialRef: '',
    refReadings: {},
  };
}

export function emptySession(): WorkbenchSession {
  return {
    draft: null,
    constraints: defaultConstraintsUI(),
    version: 0,
    undo: null,
  };
}

export function sessionFromDraft(
  draft: import('../line-draft.ts').LineDraft,
  constraints: ConstraintsUI = defaultConstraintsUI(),
): WorkbenchSession {
  return {
    draft: { ...draft, version: Math.max(1, draft.version) },
    constraints,
    version: Math.max(1, draft.version),
    undo: null,
  };
}
