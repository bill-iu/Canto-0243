/** MatchSpec apply pipeline — F1–F5 orchestration. */
import type { Database } from '../../sqljs.ts';
import { throwIfSearchCancelled, yieldToMainThread, type ShouldCancel } from '../../search-cancel.ts';
import { queryWordsByEqualsSpec } from '../equals-filters.ts';
import { getCompoundCandidatesForSpec } from '../sources.ts';
import type { CanonicalMatchSpec } from '../canonical.ts';
import { canonicalizeLegacyMatchSpec } from '../canonical.ts';
import type { MatchSpec } from '../spec.ts';
import type { WordRow } from '../word-row.ts';
import { getWordCode, getWordText } from '../word-row.ts';
import {
  filterWordsByCodeAndMask,
  hasCodeDigitConstraints,
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
  spec: CanonicalMatchSpec,
  mode: string,
  db: Database,
  shouldCancel?: ShouldCancel,
  options: { phonemeIndexPrefiltered?: boolean } = {},
): Promise<WordRow[]> {
  throwIfSearchCancelled(shouldCancel);
  if (
    spec.candidate_scope === 'complete'
    && !(spec.slots ?? []).length
    && Boolean(spec.mask)
    && [...(spec.mask ?? '')].every((char) => char === '?' || char === '_' || char === '%')
  ) {
    const rows: WordRow[] = [];
    for (let index = 0; index < candidates.length; index += 1) {
      const row = candidates[index]!;
      if (getWordText(row).length === spec.width && Boolean(getWordCode(row))) rows.push(row);
      if (index > 0 && index % 2048 === 0) {
        throwIfSearchCancelled(shouldCancel);
        await yieldToMainThread();
      }
    }
    return rows;
  }
  const anchorCount = spec.slots.filter(
    (slot) => slot.kind === 'final_anchor' || slot.kind === 'initial_anchor',
  ).length;
  if (
    spec.width === 4
    && anchorCount >= 2
    && spec.mask.includes('?')
    && spec.slots.some((slot) => slot.kind === 'final_anchor')
  ) {
    const slotOptions = await partialMaskSlotOptions(spec, db, 'final');
    return candidates.filter((w) => wordPassesPartialRhymeMaskSpec(spec, w, slotOptions));
  }
  if (
    spec.width === 4
    && anchorCount >= 2
    && spec.mask.includes('?')
    && spec.slots.some((slot) => slot.kind === 'initial_anchor')
  ) {
    const slotOptions = await partialMaskSlotOptions(spec, db, 'initial');
    return candidates.filter((w) => wordPassesPartialInitialMaskSpec(spec, w, slotOptions));
  }

  let pool = narrowByJyutpingLetterSlots(candidates, spec.slots ?? [], db);
  throwIfSearchCancelled(shouldCancel);
  // Engine phoneme inverted-index already narrowed single-slot anchors
  if (!options.phonemeIndexPrefiltered) {
    pool = await narrowByPhonemeAnchors(pool, spec.slots ?? [], db);
  }
  return filterWordsByCodeAndMask(
    pool,
    spec,
    mode,
    db,
    shouldCancel,
    options.phonemeIndexPrefiltered,
  );
}

/** ponytail: equals path in equals-filters.ts (MF-5 F4) */
export async function applyMatchSpec(
  input: CanonicalMatchSpec | MatchSpec,
  candidates: WordRow[],
  db: Database,
  mode = 'm1',
  shouldCancel?: ShouldCancel,
  options: { phonemeIndexPrefiltered?: boolean } = {},
): Promise<WordRow[]> {
  const spec = 'candidate_scope' in input ? input : canonicalizeLegacyMatchSpec(input);
  throwIfSearchCancelled(shouldCancel);
  if (spec.equals_span) {
    let rows = await queryWordsByEqualsSpec(spec, db, mode);
    if (hasCodeDigitConstraints(spec)) {
      rows = await filterWordsByCodeAndMask(rows, spec, mode, db, shouldCancel);
    }
    return rows;
  }
  if (spec.compound) {
    const pool = await getCompoundCandidatesForSpec(spec, db, mode);
    return filterCandidatesByMatchSpec(pool, spec, mode, db, shouldCancel, options);
  }
  return filterCandidatesByMatchSpec(candidates, spec, mode, db, shouldCancel, options);
}
