/** MF-5 F1 — code_digit / mask literal / position filter orchestration. */
import { getCodeVariants } from '../../code-variants.ts';
import type { Database } from '../../sqljs.ts';
import { pronRankSortValueForWord } from '../../ranking.ts';
import { throwIfSearchCancelled, yieldToMainThread, type ShouldCancel } from '../../search-cancel.ts';
import { matchesMaskLiteralChars } from '../mask-adapter.ts';
import type { CanonicalMatchSpec } from '../canonical.ts';
import type { MatchSpec } from '../spec.ts';
import { getRhymeFinals, getWordCode, getWordParts, getWordText, type WordRow } from '../word-row.ts';
import {
  anchorPhonemeOptions,
  matchesPhonemeAtPosition,
} from './f2-phoneme-anchor.ts';
import { JYUTPING_LETTER_KINDS, slotConstraintMatches } from './f3-letters.ts';

export function normalizeMode(mode: string): 'm1' | 'm2' | 'm3' {
  if (mode === 'm2' || mode === '02493') return 'm2';
  if (mode === 'm3' || mode === '394052') return 'm3';
  return 'm1';
}

export function matchesCodePositions(
  codeStr: string,
  requiredCodes: Array<string | null>,
  mode: string,
): boolean {
  /** 逐格 digit 鬆檔；required 可短於 code（前綴）；null 格跳過。 */
  if (!requiredCodes.length) {
    return true;
  }
  if (!codeStr && requiredCodes.some((r) => r != null)) {
    return false;
  }
  const searchMode = normalizeMode(mode);
  for (let idx = 0; idx < requiredCodes.length; idx++) {
    const req = requiredCodes[idx];
    if (!req) {
      continue;
    }
    if (idx >= codeStr.length) {
      return false;
    }
    const variants = new Set(getCodeVariants(req, searchMode));
    if (!variants.has(codeStr[idx]!)) {
      return false;
    }
  }
  return true;
}
export async function wordPassesPositionFilters(
  word: WordRow,
  spec: CanonicalMatchSpec,
  requiredCodes: Array<string | null>,
  mode: string,
  db: Database,
  literalChar: string | null,
  phonemeOptCache?: Map<string, Set<string>>,
  phonemeIndexPrefiltered = false,
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
    if (!matchesCodePositions(code, requiredCodes, spec.code_mode ?? mode)) {
      return false;
    }
  }
  const skipPhoneme = phonemeIndexPrefiltered;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'tone_class') {
      const digit = code[slot.pos];
      const isPing = digit === '0' || digit === '3';
      if ((slot.value === 'ping' && !isPing) || (slot.value === 'ze' && isPing)) {
        return false;
      }
    }
    if (!skipPhoneme && (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor')) {
      const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
      if (
        !(await matchesPhonemeAtPosition(
          word,
          slot.pos,
          String(slot.value ?? ''),
          constraint,
          db,
          phonemeOptCache,
        ))
      ) {
        return false;
      }
    }
    if (JYUTPING_LETTER_KINDS.has(slot.kind) && !slotConstraintMatches(word, slot, db)) {
      return false;
    }
  }
  return true;
}

export function buildRequiredCodes(spec: CanonicalMatchSpec): Array<string | null> {
  /** PR-A: mask digit + code_digit slots only — never code_prefix blob. */
  const required: Array<string | null> = Array(spec.width).fill(null);
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

export function denseCodeFromRequired(required: Array<string | null>): string | null {
  if (!required.length) {
    return null;
  }
  const parts: string[] = [];
  for (const d of required) {
    if (d == null || !/^\d$/.test(d)) {
      return null;
    }
    parts.push(d);
  }
  return parts.join('');
}

export function requiredCodesFromDigitString(digits: string): Array<string | null> {
  if (!digits || !/^\d+$/.test(digits)) {
    return [];
  }
  return [...digits];
}

export function codeDigitStringFromSpec(spec: CanonicalMatchSpec): string | null {
  const dense = denseCodeFromRequired(buildRequiredCodes(spec));
  if (dense) {
    return dense;
  }
  const parts = buildRequiredCodes(spec).filter((d): d is string => d != null && /^\d$/.test(d));
  return parts.length ? parts.join('') : null;
}

export function hasCodeDigitConstraints(spec: CanonicalMatchSpec): boolean {
  return buildRequiredCodes(spec).some((d) => d != null);
}

export function appendCodeDigitSlots(spec: MatchSpec, digits: string | null | undefined): void {
  if (!digits || !/^\d+$/.test(digits)) {
    return;
  }
  if (!spec.slots) {
    spec.slots = [];
  }
  for (let i = 0; i < digits.length && i < spec.width; i++) {
    if (spec.slots.some((s) => s.kind === 'code_digit' && s.pos === i)) {
      continue;
    }
    spec.slots.push({ pos: i, kind: 'code_digit', value: digits[i]! });
  }
}

export function groupCandidatesByChar(candidates: WordRow[]): Map<string, WordRow[]> {
  const grouped = new Map<string, WordRow[]>();
  for (const word of candidates) {
    const char = getWordText(word);
    const list = grouped.get(char) ?? [];
    list.push(word);
    grouped.set(char, list);
  }
  return grouped;
}

export function preferredPronunciationRows(rows: WordRow[]): WordRow[] {
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

export async function filterWordsByCodeAndMask(
  candidates: WordRow[],
  spec: CanonicalMatchSpec,
  mode: string,
  db: Database,
  shouldCancel?: ShouldCancel,
  phonemeIndexPrefiltered = false,
): Promise<WordRow[]> {
  let literalChar: string | null = null;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'literal_char' && slot.pos === spec.width - 1) {
      literalChar = String(slot.value ?? '');
    }
  }
  const requiredCodes = buildRequiredCodes(spec);
  const hasCodeDigitConstraints = requiredCodes.some((req) => req != null);
  const skipPhoneme = phonemeIndexPrefiltered;
  // One phoneme-options SQL per anchor char, shared across all candidates
  const phonemeOptCache = new Map<string, Set<string>>();
  if (!skipPhoneme) {
    for (const slot of spec.slots ?? []) {
      if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') {
        const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
        const anchor = String(slot.value ?? '');
        const key = `${constraint}\0${anchor}`;
        if (!phonemeOptCache.has(key)) {
          phonemeOptCache.set(key, await anchorPhonemeOptions(db, anchor, constraint));
        }
      }
    }
  }
  const out: WordRow[] = [];
  let n = 0;
  if (hasCodeDigitConstraints) {
    for (const group of groupCandidatesByChar(candidates).values()) {
      for (const word of preferredPronunciationRows(group)) {
        n += 1;
        if (n % 256 === 0) {
          throwIfSearchCancelled(shouldCancel);
          await yieldToMainThread();
        }
        if (
          await wordPassesPositionFilters(
            word,
            spec,
            requiredCodes,
            mode,
            db,
            literalChar,
            phonemeOptCache,
            skipPhoneme,
          )
        ) {
          out.push(word);
          break;
        }
      }
    }
    return out;
  }
  for (const word of candidates) {
    n += 1;
    if (n % 256 === 0) {
      throwIfSearchCancelled(shouldCancel);
      await yieldToMainThread();
    }
    if (
      await wordPassesPositionFilters(
        word,
        spec,
        requiredCodes,
        mode,
        db,
        literalChar,
        phonemeOptCache,
        skipPhoneme,
      )
    ) {
      out.push(word);
    }
  }
  return out;
}

export async function narrowByPhonemeAnchors(
  candidates: WordRow[],
  slots: ReadonlyArray<Pick<CanonicalMatchSpec['slots'][number], 'pos' | 'kind' | 'value'>>,
  db: Database,
): Promise<WordRow[]> {
  let narrowed = candidates;
  const phonemeOptCache = new Map<string, Set<string>>();
  for (const slot of slots) {
    if (slot.kind !== 'final_anchor' && slot.kind !== 'initial_anchor') {
      continue;
    }
    const constraint = slot.kind === 'final_anchor' ? 'final' : 'initial';
    const anchor = String(slot.value ?? '');
    const key = `${constraint}\0${anchor}`;
    if (!phonemeOptCache.has(key)) {
      phonemeOptCache.set(key, await anchorPhonemeOptions(db, anchor, constraint));
    }
    const options = phonemeOptCache.get(key)!;
    const next: WordRow[] = [];
    for (const w of narrowed) {
      const parts = constraint === 'final' ? getRhymeFinals(w) : getWordParts(w, 'initials');
      if (options.size && slot.pos < parts.length && options.has(parts[slot.pos]!)) {
        next.push(w);
      }
    }
    narrowed = next;
  }
  return narrowed;
}
