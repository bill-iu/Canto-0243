/** MF-5 F2 — final_anchor / initial_anchor + partial mask. */
import { queryRows } from '../../database-backend.ts';
import type { Database } from '../../sqljs.ts';
import { expandFinalOptions } from '../../rhyme-match-profile.ts';
import { getRhymeProfile } from '../../rhyme-profile-context.ts';
import { eligibleForAnchorPhonemeUnion } from '../../ranking.ts';
import { getCandidatesWithLiteralAt } from '../sources.ts';
import type { CanonicalMatchSpec } from '../canonical.ts';
import { getRhymeFinals, getWordParts, getWordText, type WordRow } from '../word-row.ts';

/** Cache anchor → phoneme options (one SQL per anchor/char, not per candidate). */
const anchorPhonemeOptionsCache = new Map<string, Set<string>>();

export function clearAnchorPhonemeOptionsCache(): void {
  anchorPhonemeOptionsCache.clear();
}

export async function anchorPhonemeOptions(
  db: Database,
  char: string,
  dimension: 'final' | 'initial',
): Promise<Set<string>> {
  const key = `${dimension}\0${char}`;
  const hit = anchorPhonemeOptionsCache.get(key);
  if (hit) return hit;

  const options = new Set<string>();
  const rows = await queryRows(
    db,
    'SELECT char, initials, finals, jyutping FROM words WHERE char = ? LIMIT 50',
    [char],
  );
  for (const row of rows) {
    const jyut = String(row.jyutping ?? '').trim();
    if (jyut && !eligibleForAnchorPhonemeUnion(char, jyut)) {
      continue;
    }
    const parts = dimension === 'final' ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (parts.length) {
      options.add(parts[0]!);
    }
  }
  anchorPhonemeOptionsCache.set(key, options);
  return options;
}

export async function matchesPhonemeAtPosition(
  word: WordRow,
  pos: number,
  anchor: string,
  constraint: 'final' | 'initial',
  db: Database,
  optionsCache?: Map<string, Set<string>>,
): Promise<boolean> {
  const cacheKey = `${constraint}\0${anchor}`;
  let options = optionsCache?.get(cacheKey);
  if (!options) {
    options = await anchorPhonemeOptions(db, anchor, constraint);
    optionsCache?.set(cacheKey, options);
  }
  const matchOpts =
    constraint === 'final' ? expandFinalOptions(options, getRhymeProfile()) : options;
  const parts = constraint === 'final' ? getRhymeFinals(word) : getWordParts(word, 'initials');
  if (!matchOpts.size || pos >= parts.length) {
    return false;
  }
  return matchOpts.has(parts[pos]!);
}
export async function contextualPhonemeOptionsAtPosition(
  db: Database,
  width: number,
  pos: number,
  anchorChar: string,
  dimension: 'final' | 'initial',
): Promise<Set<string>> {
  const options = new Set<string>();
  const rows = await getCandidatesWithLiteralAt(db, width, pos, anchorChar);
  for (const row of rows) {
    const parts = dimension === 'final' ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (parts.length > pos && parts[pos]) {
      options.add(parts[pos]!);
    }
  }
  for (const opt of await anchorPhonemeOptions(db, anchorChar, dimension)) {
    options.add(opt);
  }
  return options;
}

export async function partialMaskSlotOptions(
  spec: CanonicalMatchSpec,
  db: Database,
  dimension: 'final' | 'initial',
): Promise<Map<string, Set<string>>> {
  const kind = dimension === 'final' ? 'final_anchor' : 'initial_anchor';
  const ctx =
    dimension === 'final'
      ? (pos: number, anchor: string) =>
          contextualPhonemeOptionsAtPosition(db, spec.width, pos, anchor, 'final')
      : (pos: number, anchor: string) =>
          contextualPhonemeOptionsAtPosition(db, spec.width, pos, anchor, 'initial');
  const out = new Map<string, Set<string>>();
  for (const slot of spec.slots ?? []) {
    if (slot.kind !== kind) {
      continue;
    }
    const key = `${slot.pos}:${slot.value}`;
    if (!out.has(key)) {
      out.set(key, await ctx(slot.pos, String(slot.value ?? '')));
    }
  }
  return out;
}

export function wordPassesPartialRhymeMaskSpec(
  spec: CanonicalMatchSpec,
  word: WordRow,
  slotOptions: Map<string, Set<string>>,
): boolean {
  const text = getWordText(word);
  if (text.length !== spec.width) {
    return false;
  }
  const finals = getRhymeFinals(word);
  if (!finals.length) {
    return false;
  }
  const profile = getRhymeProfile();
  for (const slot of spec.slots ?? []) {
    if (slot.kind !== 'final_anchor') {
      continue;
    }
    const options = slotOptions.get(`${slot.pos}:${slot.value}`);
    const matchOpts = expandFinalOptions(options, profile);
    if (!matchOpts.size || slot.pos >= finals.length || !matchOpts.has(finals[slot.pos]!)) {
      return false;
    }
  }
  return true;
}

export function wordPassesPartialInitialMaskSpec(
  spec: CanonicalMatchSpec,
  word: WordRow,
  slotOptions: Map<string, Set<string>>,
): boolean {
  const text = getWordText(word);
  if (text.length !== spec.width) {
    return false;
  }
  const initials = getWordParts(word, 'initials');
  if (!initials.length) {
    return false;
  }
  const mask = spec.mask ?? '';
  for (let pos = 0; pos < mask.length; pos++) {
    const ch = mask[pos]!;
    if (ch !== '?' && text[pos] !== ch) {
      return false;
    }
  }
  for (const slot of spec.slots ?? []) {
    if (slot.kind !== 'initial_anchor') {
      continue;
    }
    const options = slotOptions.get(`${slot.pos}:${slot.value}`);
    if (!options?.size || slot.pos >= initials.length || !options.has(initials[slot.pos]!)) {
      return false;
    }
  }
  return true;
}
