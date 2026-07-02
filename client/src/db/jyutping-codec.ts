/**
 * Jyutping codec — port of app/utils/jyutping_codec.py (subset)
 */
const VOWELS = 'aeiou';

export const STANDALONE_NASAL_FINALS = new Set(['m', 'ng']);

export function splitJyutping(jyutping: string): [string[], string[], (number | null)[]] {
  if (!jyutping?.trim()) {
    return [[], [], []];
  }
  const initials: string[] = [];
  const finals: string[] = [];
  const tones: Array<number | null> = [];

  for (const syllableText of jyutping.trim().split(/\s+/)) {
    let tone: number | null = null;
    let syllable = syllableText;
    for (let i = syllableText.length - 1; i >= 0; i--) {
      if (syllableText[i]! >= '0' && syllableText[i]! <= '9') {
        tone = Number.parseInt(syllableText[i]!, 10);
        syllable = syllableText.slice(0, i);
        break;
      }
    }

    if (syllable === 'm' || syllable === 'ng') {
      initials.push(syllable);
      finals.push('');
      tones.push(tone);
      continue;
    }

    let splitPos = -1;
    for (let i = 0; i < syllable.length; i++) {
      if (VOWELS.includes(syllable[i]!)) {
        splitPos = i;
        break;
      }
    }
    let initial = splitPos !== -1 ? syllable.slice(0, splitPos) : syllable;
    let final = splitPos !== -1 ? syllable.slice(splitPos) : '';

    if (splitPos >= 2 && syllable[splitPos - 1] === 'y' && final) {
      initial = syllable.slice(0, splitPos - 1);
      final = `y${final}`;
    }

    initials.push(initial);
    finals.push(final);
    tones.push(tone);
  }
  return [initials, finals, tones];
}

export function rhymeFinalsFromJyutping(jyutping: string): string[] {
  const [, finals] = splitJyutping(jyutping);
  return finals;
}

export function syllableLetters(token: string): string {
  const t = (token ?? '').trim().toLowerCase();
  for (let i = t.length - 1; i >= 0; i--) {
    if (t[i]! >= '0' && t[i]! <= '9') {
      return t.slice(0, i);
    }
  }
  return t;
}

export function isStandaloneNasalSyllableToken(token: string): boolean {
  return STANDALONE_NASAL_FINALS.has(syllableLetters(token));
}

export function rhymeFinalIndexKeysPerPosition(jyutping: string): Set<string>[] {
  const keys: Set<string>[] = [];
  for (const token of (jyutping ?? '').trim().split(/\s+/).filter(Boolean)) {
    const letters = syllableLetters(token);
    if (STANDALONE_NASAL_FINALS.has(letters)) {
      keys.push(new Set(STANDALONE_NASAL_FINALS));
      continue;
    }
    const [, finals] = splitJyutping(token);
    const final = finals[0] ?? '';
    keys.push(final ? new Set([final]) : new Set());
  }
  return keys;
}

/** ponytail: runnable self-check */
export function jyutpingCodecSelfCheck(): void {
  const [, finals] = splitJyutping('zyu6');
  if (finals[0] !== 'yu') {
    throw new Error(`jyutpingCodecSelfCheck: zyu6 final ${finals[0]}`);
  }
  const [, fuFinals] = splitJyutping('fu6');
  if (fuFinals[0] !== 'u') {
    throw new Error(`jyutpingCodecSelfCheck: fu6 final ${fuFinals[0]}`);
  }
  const keys = rhymeFinalIndexKeysPerPosition('m4');
  if (!keys[0]?.has('m') || !keys[0]?.has('ng')) {
    throw new Error('jyutpingCodecSelfCheck: m4 nasal keys');
  }
}
