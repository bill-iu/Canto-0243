/** MF-5 F3 — jyutping letter slots (rhyme/syllable/initial_letters). */
import type { Database } from '../../sqljs.ts';
import { matchesJyutpingAnchorAtPosition } from '../../jyutping-anchor.ts';
import type { CanonicalMatchSpec } from '../canonical.ts';
import type { WordRow } from '../word-row.ts';

export const JYUTPING_LETTER_KINDS = new Set([
  'rhyme_letters',
  'syllable_letters',
  'initial_letters',
]);

type PositionSlot = Pick<CanonicalMatchSpec['slots'][number], 'pos' | 'kind' | 'value'>;

export function slotConstraintMatches(word: WordRow, slot: PositionSlot, _db: Database): boolean {
  if (!JYUTPING_LETTER_KINDS.has(slot.kind)) {
    return false;
  }
  return matchesJyutpingAnchorAtPosition(
    word,
    slot.pos,
    slot.kind as 'rhyme_letters' | 'syllable_letters' | 'initial_letters',
    String(slot.value ?? ''),
  );
}

export function narrowByJyutpingLetterSlots(
  candidates: WordRow[],
  slots: ReadonlyArray<PositionSlot>,
  db: Database,
): WordRow[] {
  let narrowed = candidates;
  for (const slot of slots) {
    if (!JYUTPING_LETTER_KINDS.has(slot.kind)) {
      continue;
    }
    narrowed = narrowed.filter((w) => slotConstraintMatches(w, slot, db));
  }
  return narrowed;
}
