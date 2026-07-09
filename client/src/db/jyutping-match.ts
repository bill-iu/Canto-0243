/** 粵拼查詢 — port of app/services/jyutping_match.py */

const TONE_DIGITS = new Set('123456');
const JYUTPING_QUERY_RE = /^[a-zA-Z0-9\s]+$/;

export interface JyutSyllable {
  letters: string;
  tone: number | null;
}

export function isJyutpingQuery(q: string): boolean {
  const t = (q || '').trim();
  if (!t || /[\u4e00-\u9fff]/.test(t)) {
    return false;
  }
  return /[a-zA-Z]/.test(t) && JYUTPING_QUERY_RE.test(t);
}

function parseSyllableToken(token: string): JyutSyllable | null {
  const raw = token.trim().toLowerCase();
  if (!raw) {
    return null;
  }
  let tone: number | null = null;
  let letters = raw;
  if (TONE_DIGITS.has(raw.at(-1)!)) {
    tone = Number(raw.at(-1));
    letters = raw.slice(0, -1);
  }
  if (!letters || !/^[a-z]+$/.test(letters)) {
    return null;
  }
  return { letters, tone };
}

export function parseJyutpingQuery(q: string): JyutSyllable[] | null {
  if (!isJyutpingQuery(q)) {
    return null;
  }
  const syllables: JyutSyllable[] = [];
  for (const token of q.trim().toLowerCase().split(/\s+/)) {
    const parsed = parseSyllableToken(token);
    if (!parsed) {
      return null;
    }
    syllables.push(parsed);
  }
  return syllables.length ? syllables : null;
}

export function parseWordJyutping(jyutping: string): JyutSyllable[] {
  if (!jyutping?.trim()) {
    return [];
  }
  const out: JyutSyllable[] = [];
  for (const token of jyutping.trim().toLowerCase().split(/\s+/)) {
    const parsed = parseSyllableToken(token);
    if (parsed) {
      out.push(parsed);
    }
  }
  return out;
}

export function normalizeJyutping(jyutping: string): string {
  return jyutping.trim().toLowerCase().split(/\s+/).join(' ');
}

export function matchesJyutpingQuery(wordJyutping: string, query: string): boolean {
  const querySyllables = parseJyutpingQuery(query);
  if (!querySyllables) {
    return false;
  }
  const wordSyllables = parseWordJyutping(wordJyutping);
  if (wordSyllables.length !== querySyllables.length) {
    return false;
  }
  if (querySyllables.every((s) => s.tone != null)) {
    return normalizeJyutping(wordJyutping) === normalizeJyutping(query);
  }
  for (let i = 0; i < wordSyllables.length; i++) {
    const wordSyl = wordSyllables[i]!;
    const querySyl = querySyllables[i]!;
    if (wordSyl.letters !== querySyl.letters) {
      return false;
    }
    if (querySyl.tone != null && wordSyl.tone !== querySyl.tone) {
      return false;
    }
  }
  return true;
}

export function expectedWordLength(query: string): number | null {
  const syllables = parseJyutpingQuery(query);
  if (!syllables) {
    return null;
  }
  if (syllables.length === 1 && syllables[0]!.tone == null) {
    return 1;
  }
  return syllables.length;
}

export function jyutpingMatchSelfCheck(): void {
  if (!matchesJyutpingQuery('nei5 hou2', 'nei hou')) {
    throw new Error('jyutping-match: nei hou');
  }
  if (!matchesJyutpingQuery('ming4 baak6', 'ming4 baak6')) {
    throw new Error('jyutping-match: ming4 baak6');
  }
  if (matchesJyutpingQuery('nei5 hou2', 'nei5')) {
    throw new Error('jyutping-match: nei5 should not match 2-syllable word');
  }
  if (expectedWordLength('nei hou') !== 2) {
    throw new Error('jyutping-match: expectedWordLength nei hou');
  }
  if (expectedWordLength('ming4') !== 1) {
    throw new Error('jyutping-match: expectedWordLength ming4');
  }
}