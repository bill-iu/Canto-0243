/**
 * Rime rhyme-letter index — port of jyutping_anchor.rhyme_letter_final_options
 */
import {
  isStandaloneNasalSyllableToken,
  rhymeFinalIndexKeysPerPosition,
  rhymeFinalsFromJyutping,
  splitJyutping,
  STANDALONE_NASAL_FINALS,
  syllableLetters,
} from './jyutping-codec.ts';

const STANDALONE_NG = 'ng';

let finalOptions: Record<string, string[]> = {};
let completeSyllables = new Set<string>();
const optionsCache = new Map<string, Set<string>>();

export function normalizeRhymeLetters(letters: string): string {
  const text = letters.trim().toLowerCase();
  return text === 'm' ? STANDALONE_NG : text;
}

export function initRhymeLetterIndex(data: {
  finalOptions?: Record<string, string[]>;
  completeSyllables?: string[];
}): void {
  finalOptions = data.finalOptions ?? {};
  completeSyllables = new Set(data.completeSyllables ?? []);
  optionsCache.clear();
}

export function isCompleteSyllableInRime(letters: string): boolean {
  return completeSyllables.has(letters.trim().toLowerCase());
}

export function syllableMatchesRhymeFragment(sylLetters: string, fragment: string): boolean {
  const frag = normalizeRhymeLetters(fragment);
  const syl = sylLetters.toLowerCase();
  if (frag === STANDALONE_NG) {
    return syl === 'm' || syl === 'ng';
  }
  if (frag.length === 1) {
    const [, finals] = splitJyutping(syl);
    return finals.length > 0 && finals[0] === frag;
  }
  return syl === frag || syl.endsWith(frag);
}

export function rhymeLetterFinalOptions(letters: string): Set<string> {
  const norm = normalizeRhymeLetters(letters);
  const cached = optionsCache.get(norm);
  if (cached) {
    return cached;
  }

  const list = finalOptions[norm];
  if (list?.length) {
    const built = new Set(list);
    optionsCache.set(norm, built);
    return built;
  }

  if (norm === STANDALONE_NG) {
    const nasal = new Set(STANDALONE_NASAL_FINALS);
    optionsCache.set(norm, nasal);
    return nasal;
  }

  const empty = new Set<string>();
  optionsCache.set(norm, empty);
  return empty;
}

export function rhymeLettersResolveOk(letters: string): boolean {
  return rhymeLetterFinalOptions(letters).size > 0;
}

export function matchesRhymeLettersAtPosition(
  word: { jyutping?: unknown; finals?: unknown },
  pos: number,
  letters: string,
): boolean {
  const fragment = normalizeRhymeLetters(letters);
  const jyut = String(word.jyutping ?? '');

  if (fragment === STANDALONE_NG) {
    const keys = rhymeFinalIndexKeysPerPosition(jyut);
    if (pos < keys.length) {
      for (const k of keys[pos]!) {
        if (STANDALONE_NASAL_FINALS.has(k)) {
          return true;
        }
      }
    }
  }

  const options = rhymeLetterFinalOptions(letters);
  if (!options.size) {
    return false;
  }

  let parts: string[] = [];
  try {
    const raw = word.finals;
    if (typeof raw === 'string' && raw.startsWith('[')) {
      parts = JSON.parse(raw) as string[];
    } else if (Array.isArray(raw)) {
      parts = raw.map(String);
    }
  } catch {
    parts = [];
  }
  if (!parts.length && jyut) {
    parts = rhymeFinalsFromJyutping(jyut);
  }
  if (pos < parts.length && options.has(parts[pos]!)) {
    return true;
  }

  const tokens = jyut.trim().split(/\s+/);
  if (pos < tokens.length) {
    const syl = syllableLetters(tokens[pos]!);
    if (syllableMatchesRhymeFragment(syl, letters)) {
      return true;
    }
    if (isStandaloneNasalSyllableToken(tokens[pos]!) && [...options].some((o) => STANDALONE_NASAL_FINALS.has(o))) {
      return true;
    }
  }
  return false;
}

export function resetRhymeLetterIndex(): void {
  finalOptions = {};
  completeSyllables = new Set();
  optionsCache.clear();
}
