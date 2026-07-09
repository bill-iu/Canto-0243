/** MatchSpec apply pipeline — F1–F5 orchestration. */
import type { Database } from '../../sqljs.ts';
import { throwIfSearchCancelled, type ShouldCancel } from '../../search-cancel.ts';
import { queryWordsByEqualsSpec } from '../equals-filters.ts';
import { getCompoundCandidatesForSpec } from '../sources.ts';
import type { MatchSpec } from '../spec.ts';
import { getEqualsSpan } from '../spec.ts';
import type { WordRow } from '../word-row.ts';
import {
  filterWordsByCodeAndMask,
  narrowByPhonemeAnchors,
} from './f1-slot-code.ts';
import {
  partialMaskSlotOptions,
  wordPassesPartialInitialMaskSpec,
  wordPassesPartialRhymeMaskSpec,
} from './f2-phoneme-anchor.ts';
import { narrowByJyutpingLetterSlots } from './f3-letters.ts';

export async function filterCandidatesByMatchSpec(
  candidates: WordRow[],
  spec: MatchSpec,
  mode: string,
  db: Database,
  shouldCancel?: ShouldCancel,
): Promise<WordRow[]> {
  throwIfSearchCancelled(shouldCancel);
  if (spec.extra?.partial_rhyme_mask) {
    const slotOptions = await partialMaskSlotOptions(spec, db, 'final');
    return candidates.filter((w) => wordPassesPartialRhymeMaskSpec(spec, w, slotOptions));
  }
  if (spec.extra?.partial_initial_mask) {
    const slotOptions = await partialMaskSlotOptions(spec, db, 'initial');
    return candidates.filter((w) => wordPassesPartialInitialMaskSpec(spec, w, slotOptions));
  }

  let pool = narrowByJyutpingLetterSlots(candidates, spec.slots ?? [], db);
  throwIfSearchCancelled(shouldCancel);
  // Engine phoneme inverted-index already narrowed single-slot anchors
  if (!spec.extra?.phoneme_index_prefiltered) {
    pool = await narrowByPhonemeAnchors(pool, spec.slots ?? [], db);
  }
  return filterWordsByCodeAndMask(pool, spec, mode, db, shouldCancel);
}

/** ponytail: equals path in equals-filters.ts (MF-5 F4) */
export async function applyMatchSpec(
  spec: MatchSpec,
  candidates: WordRow[],
  db: Database,
  mode = 'm1',
  shouldCancel?: ShouldCancel,
): Promise<WordRow[]> {
  throwIfSearchCancelled(shouldCancel);
  if (getEqualsSpan(spec)) {
    return queryWordsByEqualsSpec(spec, db, mode);
  }
  if (spec.compound_kind) {
    const pool = await getCompoundCandidatesForSpec(spec, db, mode);
    return filterCandidatesByMatchSpec(pool, spec, mode, db, shouldCancel);
  }
  return filterCandidatesByMatchSpec(candidates, spec, mode, db, shouldCancel);
}
