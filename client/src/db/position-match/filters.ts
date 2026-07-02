/**
 * MatchSpec filters — port of position_match/filters.py (MF-4 + MF-5 F1–F5)
 */
import { getCodeVariants } from '../code-variants.ts';
import { matchesJyutpingAnchorAtPosition } from '../jyutping-anchor.ts';
import type { Database } from '../sqljs.ts';
import { pronRankSortValueForWord } from '../ranking.ts';
import { queryWordsByEqualsSpec } from './equals-filters.ts';
import { matchesMaskLiteralChars } from './mask-adapter.ts';
import { getCandidatesForLength, getCompoundCandidatesForSpec } from './sources.ts';
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

function equalsAuthoritativeRow(db: Database, char: string): WordRow | null {
  const stmt = db.prepare(
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
  );
  stmt.bind([char]);
  const row = stmt.step() ? (stmt.getAsObject() as WordRow) : null;
  stmt.free();
  return row;
}

function anchorPhonemeOptions(
  db: Database,
  char: string,
  dimension: 'final' | 'initial',
): Set<string> {
  const options = new Set<string>();
  const row = equalsAuthoritativeRow(db, char);
  if (row) {
    const parts = dimension === 'final' ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (parts.length) {
      options.add(parts[0]!);
    }
  }
  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping FROM words WHERE char LIKE ? LIMIT 200',
  );
  stmt.bind([`%${char}%`]);
  while (stmt.step()) {
    const hit = stmt.getAsObject() as WordRow;
    const text = getWordText(hit);
    for (let idx = 0; idx < text.length; idx++) {
      if (text[idx] !== char) {
        continue;
      }
      const parts = dimension === 'final' ? getRhymeFinals(hit) : getWordParts(hit, 'initials');
      if (parts.length > idx && parts[idx]) {
        options.add(parts[idx]!);
      }
    }
  }
  stmt.free();
  return options;
}

export function matchesPhonemeAtPosition(
  word: WordRow,
  pos: number,
  anchor: string,
  constraint: 'final' | 'initial',
  db: Database,
): boolean {
  const options = anchorPhonemeOptions(db, anchor, constraint);
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

function contextualPhonemeOptionsAtPosition(
  db: Database,
  width: number,
  pos: number,
  anchorChar: string,
  dimension: 'final' | 'initial',
): Set<string> {
  const options = new Set<string>();
  const [rows] = getCandidatesForLength(db, width);
  for (const row of rows) {
    const text = getWordText(row);
    if (text.length !== width || text[pos] !== anchorChar) {
      continue;
    }
    const parts = dimension === 'final' ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (parts.length > pos && parts[pos]) {
      options.add(parts[pos]!);
    }
  }
  for (const opt of anchorPhonemeOptions(db, anchorChar, dimension)) {
    options.add(opt);
  }
  return options;
}

function partialMaskSlotOptions(
  spec: MatchSpec,
  db: Database,
  dimension: 'final' | 'initial',
): Map<string, Set<string>> {
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
      out.set(key, ctx(slot.pos, String(slot.value ?? '')));
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

function wordPassesPositionFilters(
  word: WordRow,
  spec: MatchSpec,
  requiredCodes: Array<string | null>,
  mode: string,
  db: Database,
  literalChar: string | null,
): boolean {
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
      if (!matchesPhonemeAtPosition(word, slot.pos, String(slot.value ?? ''), constraint, db)) {
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

function filterWordsByCodeAndMask(
  candidates: WordRow[],
  spec: MatchSpec,
  mode: string,
  db: Database,
): WordRow[] {
  let literalChar: string | null = null;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'literal_char' && slot.pos === spec.width - 1) {
      literalChar = String(slot.value ?? '');
    }
  }
  const requiredCodes = buildRequiredCodes(spec);
  const hasCodeDigitConstraints = requiredCodes.some((req) => req != null);
  const out: WordRow[] = [];
  if (hasCodeDigitConstraints) {
    for (const group of groupCandidatesByChar(candidates).values()) {
      for (const word of preferredPronunciationRows(group)) {
        if (wordPassesPositionFilters(word, spec, requiredCodes, mode, db, literalChar)) {
          out.push(word);
          break;
        }
      }
    }
    return out;
  }
  for (const word of candidates) {
    if (wordPassesPositionFilters(word, spec, requiredCodes, mode, db, literalChar)) {
      out.push(word);
    }
  }
  return out;
}

function narrowByPhonemeAnchors(candidates: WordRow[], slots: SlotConstraint[], db: Database): WordRow[] {
  let narrowed = candidates;
  for (const slot of slots) {
    if (slot.kind !== 'final_anchor' && slot.kind !== 'initial_anchor') {
      continue;
    }
    const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
    narrowed = narrowed.filter((w) =>
      matchesPhonemeAtPosition(w, slot.pos, String(slot.value ?? ''), constraint, db),
    );
  }
  return narrowed;
}

export function filterCandidatesByMatchSpec(
  candidates: WordRow[],
  spec: MatchSpec,
  mode: string,
  db: Database,
): WordRow[] {
  if (spec.extra?.partial_rhyme_mask) {
    const slotOptions = partialMaskSlotOptions(spec, db, 'final');
    return candidates.filter((w) => wordPassesPartialRhymeMaskSpec(spec, w, slotOptions));
  }
  if (spec.extra?.partial_initial_mask) {
    const slotOptions = partialMaskSlotOptions(spec, db, 'initial');
    return candidates.filter((w) => wordPassesPartialInitialMaskSpec(spec, w, slotOptions));
  }

  let pool = narrowByJyutpingLetterSlots(candidates, spec.slots ?? [], db);
  pool = narrowByPhonemeAnchors(pool, spec.slots ?? [], db);
  return filterWordsByCodeAndMask(pool, spec, mode, db);
}

function buildFinalOptionsAtPositions(
  db: Database,
  refChars: string,
  startPos: number,
  width: number,
): Array<Set<string> | null> {
  const target: Array<Set<string> | null> = Array.from({ length: width }, () => null);
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos >= 0 && pos < width) {
      const opts = anchorPhonemeOptions(db, refChars[i]!, 'final');
      if (opts.size) {
        target[pos] = opts;
      }
    }
  }
  return target;
}

function matchesHybridRefChars(
  wordChar: string,
  wordFinals: string[],
  refChars: string,
  startPos: number,
  targetFinalOptions: Array<Set<string> | null>,
): boolean {
  const width = targetFinalOptions.length;
  if (wordChar.length !== width || wordFinals.length !== width) {
    return false;
  }
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos < 0 || pos >= width) {
      return false;
    }
    if (wordChar[pos] === refChars[i]) {
      continue;
    }
    const options = targetFinalOptions[pos];
    if (options?.size && wordFinals[pos] && options.has(wordFinals[pos]!)) {
      continue;
    }
    return false;
  }
  return true;
}

export function filterHybridRefCandidates(
  candidates: WordRow[],
  spec: MatchSpec,
  mode: string,
  db: Database,
): WordRow[] {
  if (spec.hybrid_ref_chars == null || spec.hybrid_ref_pos == null) {
    return candidates;
  }
  const targetFinalOptions = buildFinalOptionsAtPositions(
    db,
    spec.hybrid_ref_chars,
    spec.hybrid_ref_pos,
    spec.width,
  );
  const allowedCodes = spec.code_prefix
    ? new Set(getCodeVariants(spec.code_prefix, normalizeMode(mode)))
    : null;
  const out: WordRow[] = [];
  for (const word of candidates) {
    const wordCode = getWordCode(word);
    if (allowedCodes && !allowedCodes.has(wordCode)) {
      continue;
    }
    const wordChar = getWordText(word);
    const wordFinals = getRhymeFinals(word);
    if (
      matchesHybridRefChars(
        wordChar,
        wordFinals,
        spec.hybrid_ref_chars,
        spec.hybrid_ref_pos,
        targetFinalOptions,
      )
    ) {
      out.push(word);
    }
  }
  return out;
}

/** ponytail: equals path in equals-filters.ts (MF-5 F4) */
export function applyMatchSpec(
  spec: MatchSpec,
  candidates: WordRow[],
  db: Database,
  mode = 'm1',
): WordRow[] {
  if (getEqualsSpan(spec)) {
    return queryWordsByEqualsSpec(spec, db, mode);
  }
  if (spec.compound_kind) {
    const pool = getCompoundCandidatesForSpec(spec, db, mode);
    return filterCandidatesByMatchSpec(pool, spec, mode, db);
  }
  if (spec.hybrid_ref_chars != null && spec.hybrid_ref_pos != null) {
    return filterHybridRefCandidates(candidates, spec, mode, db);
  }
  return filterCandidatesByMatchSpec(candidates, spec, mode, db);
}
