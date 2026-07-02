/**
 * Jyutping anchor matching — port of app/services/jyutping_anchor.py
 */
import { isStandaloneNasalSyllableToken, syllableLetters } from './jyutping-codec.ts';
import {
  isCompleteSyllableInRime,
  matchesRhymeLettersAtPosition,
  normalizeRhymeLetters,
  rhymeLettersResolveOk,
} from './rime-index.ts';

export type AnchorKind = 'initial_letters' | 'rhyme_letters' | 'syllable_letters';

/** Python CODE_TAIL_MIDDLE — jyutping slot connector is `+`, not legacy ∕ */
const CODE_SLOT = '+';

const VOWEL_RHYME_LETTERS = new Set(['a', 'e', 'i', 'o', 'u']);
const AMBIGUOUS_PHONEME_LETTERS = new Set(['m', 'ng']);
const INITIAL_CLUSTERS = new Set(['ng', 'gw', 'kw']);

export type JyutpingAnchorParsed = {
  raw_q: string;
  width: number;
  anchor_pos: number;
  anchor_kind: AnchorKind;
  anchor_value: string;
  dual_phoneme?: boolean;
  code_prefix?: string;
  equals_style?: boolean;
  code_slots?: Array<[number, string]>;
  hybrid_rhyme?: boolean;
  dual_initial_value?: string;
};

function isHybridRhymeLetters(letters: string): boolean {
  const text = letters.trim().toLowerCase();
  if (VOWEL_RHYME_LETTERS.has(text) || AMBIGUOUS_PHONEME_LETTERS.has(text)) {
    return true;
  }
  return classifyLatinAnchor(text) === 'rhyme_letters';
}

function anchorValueForKind(kind: AnchorKind, letters: string): string | null {
  const lower = letters.toLowerCase();
  if (kind === 'rhyme_letters') {
    const value = normalizeRhymeLetters(lower);
    if (!rhymeLettersResolveOk(value)) {
      return null;
    }
    return value;
  }
  return lower;
}

export function classifyLatinAnchor(letters: string): AnchorKind | null {
  const text = (letters ?? '').trim().toLowerCase();
  if (!text || !/^[a-z]+$/.test(text)) {
    return null;
  }
  if (VOWEL_RHYME_LETTERS.has(text) || text === 'ng') {
    return 'rhyme_letters';
  }
  if (text.length === 1) {
    return 'initial_letters';
  }
  if (isCompleteSyllableInRime(text)) {
    return 'syllable_letters';
  }
  return 'rhyme_letters';
}

export function parseSyllableLetterTokens(jyutping: string): string[] {
  return jyutping
    .trim()
    .split(/\s+/)
    .map((s) => syllableLetters(s));
}

function matchesSyllableLettersAtPosition(
  word: { jyutping?: unknown },
  pos: number,
  letters: string,
): boolean {
  const syls = parseSyllableLetterTokens(String(word.jyutping ?? ''));
  return pos < syls.length && syls[pos] === letters.toLowerCase();
}

function matchesInitialLettersAtPosition(
  word: { jyutping?: unknown; initials?: unknown },
  pos: number,
  letter: string,
): boolean {
  const jyut = String(word.jyutping ?? '');
  const tokens = jyut.trim().split(/\s+/);
  if (pos < tokens.length && isStandaloneNasalSyllableToken(tokens[pos]!)) {
    return false;
  }
  let parts: string[] = [];
  try {
    const raw = word.initials;
    if (typeof raw === 'string' && raw.startsWith('[')) {
      parts = JSON.parse(raw) as string[];
    }
  } catch {
    parts = [];
  }
  return pos < parts.length && parts[pos] === letter.toLowerCase();
}

export function matchesJyutpingAnchorAtPosition(
  word: { jyutping?: unknown; initials?: unknown; finals?: unknown },
  pos: number,
  kind: AnchorKind,
  value: string,
): boolean {
  const letters = value.toLowerCase();
  if (kind === 'syllable_letters') {
    return matchesSyllableLettersAtPosition(word, pos, letters);
  }
  if (kind === 'initial_letters') {
    return matchesInitialLettersAtPosition(word, pos, letters);
  }
  if (kind === 'rhyme_letters') {
    return matchesRhymeLettersAtPosition(word, pos, letters);
  }
  return false;
}

function parseDualPhonemeAnchorQuery(q: string): JyutpingAnchorParsed | null {
  let m = q.match(/^\?\+?([a-zA-Z]+)\?$/i);
  if (m) {
    const letters = m[1]!.toLowerCase();
    if (AMBIGUOUS_PHONEME_LETTERS.has(letters)) {
      return {
        raw_q: q,
        width: 3,
        anchor_pos: 1,
        anchor_kind: 'rhyme_letters',
        anchor_value: normalizeRhymeLetters(letters),
        dual_phoneme: true,
        dual_initial_value: letters,
      };
    }
  }
  m = q.match(/^(\d+)(m|ng)(\d+)$/i);
  if (m) {
    const left = m[1]!;
    const letters = m[2]!.toLowerCase();
    const right = m[3]!;
    return {
      raw_q: q,
      width: left.length + right.length,
      anchor_pos: Math.max(0, left.length - 1),
      anchor_kind: 'rhyme_letters',
      anchor_value: normalizeRhymeLetters(letters),
      code_prefix: left + right,
      equals_style: true,
      dual_phoneme: true,
      dual_initial_value: letters,
    };
  }
  return null;
}

function parseTripleJyutpingSlotQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^\?\+?([a-zA-Z]+)\?$/i);
  if (!m) {
    return null;
  }
  const letters = m[1]!;
  const kind = classifyLatinAnchor(letters);
  if (!kind) {
    return null;
  }
  const value = anchorValueForKind(kind, letters);
  if (!value) {
    return null;
  }
  return {
    raw_q: q,
    width: 3,
    anchor_pos: 1,
    anchor_kind: kind,
    anchor_value: value,
  };
}

function parseEndJyutpingSyllableQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^\?\+?([a-zA-Z]+)$/i);
  if (!m) {
    return null;
  }
  const letters = m[1]!.toLowerCase();
  if (classifyLatinAnchor(letters) !== 'syllable_letters') {
    return null;
  }
  return {
    raw_q: q,
    width: 2,
    anchor_pos: 1,
    anchor_kind: 'syllable_letters',
    anchor_value: letters,
  };
}

function parseCodeSyllableThreeQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d)[?+]([a-zA-Z]+)(\d)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (classifyLatinAnchor(letters) !== 'syllable_letters') {
    return null;
  }
  return {
    raw_q: q,
    width: 3,
    anchor_pos: 1,
    anchor_kind: 'syllable_letters',
    anchor_value: letters,
    code_prefix: m[1]! + m[3]!,
    code_slots: [
      [0, m[1]!],
      [2, m[3]!],
    ],
  };
}

function parseCodeRhymeThreeQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d)[?+]([a-zA-Z]+)(\d)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (classifyLatinAnchor(letters) !== 'rhyme_letters') {
    return null;
  }
  const value = anchorValueForKind('rhyme_letters', letters);
  if (!value) {
    return null;
  }
  return {
    raw_q: q,
    width: 3,
    anchor_pos: 1,
    anchor_kind: 'rhyme_letters',
    anchor_value: value,
    code_prefix: m[1]! + m[3]!,
    code_slots: [
      [0, m[1]!],
      [2, m[3]!],
    ],
  };
}

function parseCodeClusterInitialQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d)(ng|gw|kw)(\d)$/i);
  if (!m) {
    return null;
  }
  const cluster = m[2]!.toLowerCase();
  if (cluster === 'ng') {
    return null;
  }
  return {
    raw_q: q,
    width: 2,
    anchor_pos: 0,
    anchor_kind: 'initial_letters',
    anchor_value: cluster,
    code_prefix: m[1]! + m[3]!,
    equals_style: true,
  };
}

function parseCodeInitialQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d)([a-z])(\d)$/i);
  if (!m) {
    return null;
  }
  const letter = m[2]!.toLowerCase();
  if (classifyLatinAnchor(letter) !== 'initial_letters') {
    return null;
  }
  return {
    raw_q: q,
    width: 2,
    anchor_pos: 0,
    anchor_kind: 'initial_letters',
    anchor_value: letter,
    code_prefix: m[1]! + m[3]!,
    equals_style: true,
  };
}

function parseCodeSyllableTwoQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d)([a-zA-Z]+)(\d)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (classifyLatinAnchor(letters) !== 'syllable_letters') {
    return null;
  }
  return {
    raw_q: q,
    width: 2,
    anchor_pos: 0,
    anchor_kind: 'syllable_letters',
    anchor_value: letters,
    code_prefix: m[1]! + m[3]!,
  };
}

function parseCodeRhymeEqualsQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d+)([a-zA-Z]+)(\d+)$/i);
  if (!m) {
    return null;
  }
  const left = m[1]!;
  const letters = m[2]!.toLowerCase();
  const right = m[3]!;
  if (left.length < 1 || right.length < 1) {
    return null;
  }
  if (classifyLatinAnchor(letters) !== 'rhyme_letters') {
    return null;
  }
  const value = anchorValueForKind('rhyme_letters', letters);
  if (!value) {
    return null;
  }
  return {
    raw_q: q,
    width: left.length + right.length,
    anchor_pos: Math.max(0, left.length - 1),
    anchor_kind: 'rhyme_letters',
    anchor_value: value,
    code_prefix: left + right,
    equals_style: true,
  };
}

function parseHybridJyutpingSyllableQuery(q: string): JyutpingAnchorParsed | null {
  if (q.includes('?')) {
    return null;
  }
  const m = q.match(/^(\d+)([a-zA-Z]+)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (classifyLatinAnchor(letters) !== 'syllable_letters') {
    return null;
  }
  const prefix = m[1]!;
  return {
    raw_q: q,
    width: prefix.length,
    anchor_pos: prefix.length - 1,
    anchor_kind: 'syllable_letters',
    anchor_value: letters,
    code_prefix: prefix,
  };
}

function parseRhymeVowelHybridQuery(q: string): JyutpingAnchorParsed | null {
  if (q.includes(CODE_SLOT)) {
    return null;
  }
  const m = q.match(/^(\d+)([a-zA-Z]+)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (!isHybridRhymeLetters(letters)) {
    return null;
  }
  const value = anchorValueForKind('rhyme_letters', letters);
  if (!value) {
    return null;
  }
  const prefix = m[1]!;
  return {
    raw_q: q,
    width: prefix.length,
    anchor_pos: prefix.length - 1,
    anchor_kind: 'rhyme_letters',
    anchor_value: value,
    code_prefix: prefix,
    hybrid_rhyme: true,
  };
}

function parseCodeRhymePlusTailQuery(q: string): JyutpingAnchorParsed | null {
  const m = q.match(/^(\d+)\+([a-zA-Z]+)$/i);
  if (!m) {
    return null;
  }
  const letters = m[2]!.toLowerCase();
  if (!isHybridRhymeLetters(letters)) {
    return null;
  }
  const value = anchorValueForKind('rhyme_letters', letters);
  if (!value) {
    return null;
  }
  const code = m[1]!;
  return {
    raw_q: q,
    width: code.length + 1,
    anchor_pos: code.length,
    anchor_kind: 'rhyme_letters',
    anchor_value: value,
    code_prefix: code,
    code_slots: [...code].map((d, i) => [i, d] as [number, string]),
    hybrid_rhyme: true,
  };
}

/** Port of jyutping_anchor.parse_jyutping_anchor_query */
export function parseJyutpingAnchorQuery(q: string): JyutpingAnchorParsed | null {
  if (!q || /[\u4e00-\u9fff]/.test(q)) {
    return null;
  }
  const parsers = [
    parseDualPhonemeAnchorQuery,
    parseTripleJyutpingSlotQuery,
    parseEndJyutpingSyllableQuery,
    parseCodeSyllableThreeQuery,
    parseCodeRhymeThreeQuery,
    parseCodeClusterInitialQuery,
    parseCodeInitialQuery,
    parseCodeSyllableTwoQuery,
    parseCodeRhymeEqualsQuery,
    parseCodeRhymePlusTailQuery,
    parseHybridJyutpingSyllableQuery,
    parseRhymeVowelHybridQuery,
  ];
  for (const parser of parsers) {
    const parsed = parser(q);
    if (parsed) {
      return parsed;
    }
  }
  return null;
}

export function isJyutpingAnchorMaskQuery(q: string): boolean {
  return parseJyutpingAnchorQuery(q) !== null;
}

export { normalizeRhymeLetters, rhymeLettersResolveOk, AMBIGUOUS_PHONEME_LETTERS, INITIAL_CLUSTERS };
