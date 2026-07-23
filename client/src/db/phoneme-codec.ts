/**
 * 音素欄位緊湊化 (ADR-0037) — must stay in lockstep with
 * app/domain/lexicon/phoneme_codec.py (S1 + K1).
 */

export const PHONEME_VOCAB_VERSION = 'j2.v1';

export const FINALS_VOCAB = [
  '',
  'a',
  'aa',
  'aai',
  'aak',
  'aam',
  'aan',
  'aang',
  'aap',
  'aat',
  'aau',
  'ai',
  'ak',
  'am',
  'an',
  'ang',
  'ap',
  'at',
  'au',
  'e',
  'ei',
  'ek',
  'em',
  'en',
  'eng',
  'eoi',
  'eon',
  'eot',
  'ep',
  'et',
  'eu',
  'i',
  'ik',
  'iks',
  'im',
  'in',
  'ing',
  'ip',
  'it',
  'iu',
  'o',
  'oe',
  'oek',
  'oeng',
  'oet',
  'oi',
  'ok',
  'on',
  'ong',
  'op',
  'ot',
  'ou',
  'u',
  'ui',
  'uk',
  'un',
  'ung',
  'ut',
  'yu',
  'yun',
  'yut',
] as const;

export const INITIALS_VOCAB = [
  '',
  '!',
  '!t',
  '!zh',
  'b',
  'c',
  'd',
  'f',
  'g',
  'gw',
  'h',
  'hm',
  'hng',
  'j',
  'k',
  'kw',
  'l',
  'm',
  'n',
  'ng',
  'p',
  's',
  't',
  'w',
  'z',
] as const;

export type PhonemeDim = 'final' | 'initial';

const FINAL_TO_ID: Map<string, number> = new Map(FINALS_VOCAB.map((t, i) => [t, i]));
const INITIAL_TO_ID: Map<string, number> = new Map(INITIALS_VOCAB.map((t, i) => [t, i]));
const ID_TO_FINAL: Map<number, string> = new Map(FINALS_VOCAB.map((t, i) => [i, t]));
const ID_TO_INITIAL: Map<number, string> = new Map(INITIALS_VOCAB.map((t, i) => [i, t]));

function maps(dim: PhonemeDim) {
  return dim === 'final'
    ? { toId: FINAL_TO_ID, idTo: ID_TO_FINAL }
    : { toId: INITIAL_TO_ID, idTo: ID_TO_INITIAL };
}

export function encodePhonemeList(parts: string[], dim: PhonemeDim): string {
  if (!parts.length) return '';
  const { toId } = maps(dim);
  const ids: string[] = [];
  for (const p of parts) {
    const token = p ?? '';
    const id = toId.get(token);
    if (id === undefined) {
      throw new Error(`unknown ${dim} phoneme token ${JSON.stringify(token)}`);
    }
    ids.push(String(id));
  }
  return ids.join('.');
}

/** M1: compact only (JSON arrays → []). Lists pass through (cache). */
export function decodePhonemeField(raw: unknown, dim: PhonemeDim): string[] {
  if (raw == null || raw === '') return [];
  if (Array.isArray(raw)) return raw.map((x) => (x == null ? '' : String(x)));
  if (typeof raw !== 'string') return [];
  const s = raw.trim();
  if (!s) return [];
  if (s[0] === '[') return [];
  const { idTo } = maps(dim);
  const out: string[] = [];
  for (const part of s.split('.')) {
    if (!part) continue;
    const idx = Number(part);
    if (!Number.isInteger(idx) || !idTo.has(idx)) return [];
    out.push(idTo.get(idx)!);
  }
  return out;
}

/** P1: suffix-aligned compact span patterns for SQL LIKE. */
export function compactSpanLikePatterns(encodedSpan: string): string[] {
  if (!encodedSpan) return [];
  return [encodedSpan, `%${encodedSpan}`, `%.${encodedSpan}`];
}
