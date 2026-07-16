/** Shared with client/src/db/phoneme-codec.ts — keep vocab in lockstep (ADR-0037). */
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
];

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
];

const FINAL_TO_ID = new Map(FINALS_VOCAB.map((t, i) => [t, i]));
const INITIAL_TO_ID = new Map(INITIALS_VOCAB.map((t, i) => [t, i]));
const ID_TO_FINAL = new Map(FINALS_VOCAB.map((t, i) => [i, t]));
const ID_TO_INITIAL = new Map(INITIALS_VOCAB.map((t, i) => [i, t]));

function maps(dim) {
  return dim === 'final'
    ? { toId: FINAL_TO_ID, idTo: ID_TO_FINAL }
    : { toId: INITIAL_TO_ID, idTo: ID_TO_INITIAL };
}

/** Compact decode; JSON arrays → []. Lists pass through. */
export function decodePhonemeField(raw, dim) {
  if (raw == null || raw === '') return [];
  if (Array.isArray(raw)) return raw.map((x) => (x == null ? '' : String(x)));
  if (typeof raw !== 'string') return [];
  const s = raw.trim();
  if (!s) return [];
  if (s[0] === '[') return [];
  const { idTo } = maps(dim);
  const out = [];
  for (const part of s.split('.')) {
    if (!part) continue;
    const idx = Number(part);
    if (!Number.isInteger(idx) || !idTo.has(idx)) return [];
    out.push(idTo.get(idx));
  }
  return out;
}
