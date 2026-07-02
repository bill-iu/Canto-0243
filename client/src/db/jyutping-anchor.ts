/**
 * Jyutping anchor matching — port of app/services/jyutping_anchor.py (subset)
 */
import { isStandaloneNasalSyllableToken, syllableLetters } from './jyutping-codec.ts';
import {
  isCompleteSyllableInRime,
  matchesRhymeLettersAtPosition,
  normalizeRhymeLetters,
  rhymeLettersResolveOk,
} from './rime-index.ts';

type AnchorKind = 'initial_letters' | 'rhyme_letters' | 'syllable_letters';

const VOWEL_RHYME_LETTERS = new Set(['a', 'e', 'i', 'o', 'u']);
const AMBIGUOUS_PHONEME_LETTERS = new Set(['m', 'ng']);

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

export { normalizeRhymeLetters, rhymeLettersResolveOk, AMBIGUOUS_PHONEME_LETTERS };
