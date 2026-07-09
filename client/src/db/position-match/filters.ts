/**
 * MatchSpec filters — port of position_match/filters.py (MF-4 + MF-5 F1–F5)
 */
import { getCodeVariants } from '../code-variants.ts';
import { queryRows } from '../database-backend.ts';
import { matchesJyutpingAnchorAtPosition } from '../jyutping-anchor.ts';
import type { Database } from '../sqljs.ts';
import { eligibleForAnchorPhonemeUnion, pronRankSortValueForWord } from '../ranking.ts';
import { throwIfSearchCancelled, type ShouldCancel } from '../search-cancel.ts';
import { queryWordsByEqualsSpec } from './equals-filters.ts';
import { matchesMaskLiteralChars } from './mask-adapter.ts';
import { getCandidatesWithLiteralAt, getCompoundCandidatesForSpec } from './sources.ts';
import type { MatchSpec, SlotConstraint } from './spec.ts';
import { getEqualsSpan } from './spec.ts';
import { getRhymeFinals, getWordCode, getWordParts, getWordText, type WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);

function normalizeMode(mode: string): 'm1' | 'm2' {
  return mode === 'm2' || mode === '02493' ? 'm2' : 'm1';
}

export function matchesCodePositions(
  codeStr: string,
  requiredCodes: Array<string | null>,
  mode: string,
): boolean {
  if (codeStr.length !== requiredCodes.length) {
    return false;
  }
  const searchMode = normalizeMode(mode);
  for (let idx = 0; idx < requiredCodes.length; idx++) {
    const req = requiredCodes[idx];
    if (!req) {
      continue;
    }
    const variants = new Set(getCodeVariants(req, searchMode));
    if (!variants.has(codeStr[idx]!)) {
      return false;
    }
  }
  return true;
}

export async function anchorPhonemeOptions(
  db: Database,
  char: string,
  dimension: 'final' | 'initial',
): Promise<Set<string>> {
  const options = new Set<string>();
  const rows = await queryRows(
    db,
    'SELECT char, initials, finals, jyutping FROM words WHERE char = ? LIMIT 50',
    [char],
  );
  for (const hit of rows) {
    const jyut = String(hit.jyutping ?? '').trim();
    if (jyut && !eligibleForAnchorPhonemeUnion(char, jyut)) {
      continue;
    }
    const parts = dimension === 'final' ? getRhymeFinals(hit) : getWordParts(hit, 'initials');
    if (parts.length) {
      options.add(parts[0]!);
    }
  }
  return options;
}

export async function matchesPhonemeAtPosition(
  word: WordRow,
  pos: number,
  anchor: string,
  constraint: 'final' | 'initial',
  db: Database,
): Promise<boolean> {
  const options = await anchorPhonemeOptions(db, anchor, constraint);
  const parts = constraint === 'final' ? getRhymeFinals(word) : getWordParts(word, 'initials');
  if (!options.size || pos >= parts.length) {
    return false;
  }
  return options.has(parts[pos]!);
}

function slotConstraintMatches(word: WordRow, slot: SlotConstraint, _db: Database): boolean {
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

function narrowByJyutpingLetterSlots(
  candidates: WordRow[],
  slots: SlotConstraint[],
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

async function contextualPhonemeOptionsAtPosition(
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

async function partialMaskSlotOptions(
  spec: MatchSpec,
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

function wordPassesPartialRhymeMaskSpec(
  spec: MatchSpec,
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
  for (const slot of spec.slots ?? []) {
    if (slot.kind !== 'final_anchor') {
      continue;
    }
    const options = slotOptions.get(`${slot.pos}:${slot.value}`);
    if (!options?.size || slot.pos >= finals.length || !options.has(finals[slot.pos]!)) {
      return false;
    }
  }
  return true;
}

function wordPassesPartialInitialMaskSpec(
  spec: MatchSpec,
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

async function wordPassesPositionFilters(
  word: WordRow,
  spec: MatchSpec,
  requiredCodes: Array<string | null>,
  mode: string,
  db: Database,
  literalChar: string | null,
): Promise<boolean> {
  const wordChar = getWordText(word);
  if (wordChar.length !== spec.width) {
    return false;
  }
  const mask = spec.mask ?? '';
  if (mask && !matchesMaskLiteralChars(wordChar, mask)) {
    return false;
  }
  if (literalChar != null && wordChar[wordChar.length - 1] !== literalChar) {
    return false;
  }
  const code = getWordCode(word);
  if (!code) {
    return false;
  }
  const needsStoredFinals = (spec.slots ?? []).some(
    (s) => s.kind === 'final_anchor' || s.kind === 'initial_anchor',
  );
  const finals = getRhymeFinals(word);
  if (needsStoredFinals && !finals.length) {
    return false;
  }
  if (requiredCodes.some((req) => req != null)) {
    if (!matchesCodePositions(code, requiredCodes, mode)) {
      return false;
    }
  }
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') {
      const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
      if (!(await matchesPhonemeAtPosition(word, slot.pos, String(slot.value ?? ''), constraint, db))) {
        return false;
      }
    }
    if (JYUTPING_LETTER_KINDS.has(slot.kind) && !slotConstraintMatches(word, slot, db)) {
      return false;
    }
  }
  return true;
}

function buildRequiredCodes(spec: MatchSpec): Array<string | null> {
  const required: Array<string | null> = Array(spec.width).fill(null);
  const hasSlotDigits = (spec.slots ?? []).some((s) => s.kind === 'code_digit');
  if (spec.code_prefix && !hasSlotDigits) {
    for (let i = 0; i < spec.code_prefix.length && i < spec.width; i++) {
      required[i] = spec.code_prefix[i]!;
    }
  }
  const mask = spec.mask ?? '';
  for (let i = 0; i < mask.length && i < spec.width; i++) {
    if (/\d/.test(mask[i]!)) {
      required[i] = mask[i]!;
    }
  }
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'code_digit' && slot.pos >= 0 && slot.pos < spec.width && slot.value != null) {
      required[slot.pos] = String(slot.value);
    }
  }
  return required;
}

function groupCandidatesByChar(candidates: WordRow[]): Map<string, WordRow[]> {
  const grouped = new Map<string, WordRow[]>();
  for (const word of candidates) {
    const char = getWordText(word);
    const list = grouped.get(char) ?? [];
    list.push(word);
    grouped.set(char, list);
  }
  return grouped;
}

function preferredPronunciationRows(rows: WordRow[]): WordRow[] {
  if (!rows.length) {
    return [];
  }
  const ranked = rows.map((word) => ({
    rank: pronRankSortValueForWord(getWordText(word), String(word.jyutping ?? '')),
    word,
  }));
  const best = Math.min(...ranked.map((r) => r.rank));
  return ranked.filter((r) => r.rank === best).map((r) => r.word);
}

async function filterWordsByCodeAndMask(
  candidates: WordRow[],
  spec: MatchSpec,
  mode: string,
  db: Database,
  shouldCancel?: ShouldCancel,
): Promise<WordRow[]> {
  let literalChar: string | null = null;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'literal_char' && slot.pos === spec.width - 1) {
      literalChar = String(slot.value ?? '');
    }
  }
  const requiredCodes = buildRequiredCodes(spec);
  const hasCodeDigitConstraints = requiredCodes.some((req) => req != null);
  const out: WordRow[] = [];
  let n = 0;
  if (hasCodeDigitConstraints) {
    for (const group of groupCandidatesByChar(candidates).values()) {
      for (const word of preferredPronunciationRows(group)) {
        n += 1;
        if (n % 64 === 0) throwIfSearchCancelled(shouldCancel);
        if (await wordPassesPositionFilters(word, spec, requiredCodes, mode, db, literalChar)) {
          out.push(word);
          break;
        }
      }
    }
    return out;
  }
  for (const word of candidates) {
    n += 1;
    if (n % 64 === 0) throwIfSearchCancelled(shouldCancel);
    if (await wordPassesPositionFilters(word, spec, requiredCodes, mode, db, literalChar)) {
      out.push(word);
    }
  }
  return out;
}

async function narrowByPhonemeAnchors(candidates: WordRow[], slots: SlotConstraint[], db: Database): Promise<WordRow[]> {
  let narrowed = candidates;
  for (const slot of slots) {
    if (slot.kind !== 'final_anchor' && slot.kind !== 'initial_anchor') {
      continue;
    }
    const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
    const next: WordRow[] = [];
    for (const w of narrowed) {
      if (await matchesPhonemeAtPosition(w, slot.pos, String(slot.value ?? ''), constraint, db)) {
        next.push(w);
      }
    }
    narrowed = next;
  }
  return narrowed;
}

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
  pool = await narrowByPhonemeAnchors(pool, spec.slots ?? [], db);
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
