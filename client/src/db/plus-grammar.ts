/** Port of app/services/query_grammar/plus.py — canonical plus → mask fast path. */

const HEAD_LITERAL_MASK_RE = /^\+([\u4e00-\u9fff][0-9_?%]+)$/;
const MIDDLE_LITERAL_MASK_RE = /^([_?%])\+([\u4e00-\u9fff])([0-9_?%]*)$/;

/** `+香??` / `?+你?` → equivalent mask literal (parity with Python mask_from_canonical_plus_query). */
export function maskFromCanonicalPlusQuery(q: string): string | null {
  if (!q || q.includes('=')) {
    return null;
  }
  let m = q.match(HEAD_LITERAL_MASK_RE);
  if (m) {
    return m[1]!;
  }
  m = q.match(MIDDLE_LITERAL_MASK_RE);
  if (m) {
    return m[1]! + m[2]! + m[3]!;
  }
  return null;
}