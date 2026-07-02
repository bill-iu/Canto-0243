/**
 * MatchSpec filters — port of position_match/filters.py (MF-4 subset)
 */
import { getCodeVariants } from '../code-variants.ts';
import type { Database } from '../sqljs.ts';
import { matchesMaskLiteralChars, requiredCodesFromSpec } from './mask-adapter.ts';
import type { MatchSpec, SlotConstraint } from './spec.ts';
import { getEqualsSpan } from './spec.ts';
import { getRhymeFinals, getWordCode, getWordParts, getWordText, type WordRow } from './word-row.ts';

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
  const finals = getRhymeFinals(word);
  if (!code || !finals.length) {
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
  }
  return true;
}

function buildRequiredCodes(spec: MatchSpec): Array<string | null> {
  const required = requiredCodesFromSpec(spec);
  const hasSlotDigits = (spec.slots ?? []).some((s) => s.kind === 'code_digit');
  if (spec.code_prefix && !hasSlotDigits) {
    for (let i = 0; i < spec.code_prefix.length && i < spec.width; i++) {
      required[i] = spec.code_prefix[i]!;
    }
  }
  return required;
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
  const out: WordRow[] = [];
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
  let pool = narrowByPhonemeAnchors(candidates, spec.slots ?? [], db);
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

/** ponytail: equals path still in query-engine until MF-6 */
export function applyMatchSpec(
  spec: MatchSpec,
  candidates: WordRow[],
  db: Database,
  mode = 'm1',
): WordRow[] {
  if (getEqualsSpan(spec)) {
    return [];
  }
  if (spec.hybrid_ref_chars != null && spec.hybrid_ref_pos != null) {
    return filterHybridRefCandidates(candidates, spec, mode, db);
  }
  return filterCandidatesByMatchSpec(candidates, spec, mode, db);
}
