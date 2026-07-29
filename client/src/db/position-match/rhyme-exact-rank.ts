/**
 * ADR-0078 R2: when 韻母比對檔 ≠ 正韻, exact-final hits rank before loose hits.
 */
import { expandFinalOptions } from '../rhyme-match-profile.ts';
import { getRhymeProfile } from '../rhyme-profile-context.ts';
import type { Database } from '../sqljs.ts';
import type { CanonicalMatchSpec } from './canonical.ts';
import { anchorPhonemeOptions } from './filters/f2-phoneme-anchor.ts';
import { getRhymeFinals, type WordRow } from './word-row.ts';

/** Precompute exact final options per final_anchor slot (no profile expand). */
export async function exactFinalSlotOptions(
  spec: CanonicalMatchSpec,
  db: Database,
): Promise<Array<{ pos: number; options: Set<string> }>> {
  const out: Array<{ pos: number; options: Set<string> }> = [];
  for (const slot of spec.slots ?? []) {
    if (slot.kind !== 'final_anchor' || !slot.value) continue;
    const options = await anchorPhonemeOptions(db, String(slot.value), 'final');
    out.push({ pos: slot.pos, options });
  }
  if (spec.equals_span && (spec.equals_span.dimension === 'final' || spec.equals_span.dimension === 'rhyme')) {
    // equals span: exact = each ref final equals word final; handled via ref_jyutping or literal options later
  }
  return out;
}

export function isExactFinalHit(
  word: WordRow,
  exactSlots: Array<{ pos: number; options: Set<string> }>,
): boolean {
  if (!exactSlots.length) return true;
  const finals = getRhymeFinals(word);
  for (const { pos, options } of exactSlots) {
    if (!options.size || pos >= finals.length || !options.has(finals[pos]!)) {
      return false;
    }
  }
  return true;
}

/** Comparator key: 0 = exact 正韻 layer, 1 = loose. */
export function exactFinalRankKey(
  word: WordRow,
  exactSlots: Array<{ pos: number; options: Set<string> }>,
): number {
  if (getRhymeProfile() === 'exact' || !exactSlots.length) return 0;
  return isExactFinalHit(word, exactSlots) ? 0 : 1;
}

/** True if a alone would match under exact (for equals span targetParts). */
export function equalsSpanExactHit(word: WordRow, targetParts: string[], startPos: number): boolean {
  const finals = getRhymeFinals(word);
  for (let i = 0; i < targetParts.length; i++) {
    const pos = startPos + i;
    const ref = targetParts[i];
    if (!ref) continue;
    if (pos >= finals.length || finals[pos] !== ref) return false;
  }
  return true;
}

/** Expand-aware has (for tests). */
export function finalInExpanded(options: Set<string>, final: string, profile: string): boolean {
  return expandFinalOptions(options, profile).has(final);
}
