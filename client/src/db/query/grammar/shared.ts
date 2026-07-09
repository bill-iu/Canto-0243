/** Shared grammar constants / equals framing. */
import { QueryKind } from '../../query-kind.ts';
import type { ParsedQuery } from '../../query-types.ts';

/** ponytail: Python CODE_TAIL_MIDDLE is `+`; TS legacy uses ∕ for plus-anchor only */
export const GRAMMAR_PLUS = '+';

/** Division slash (∕) — legacy plus-anchor separator in some paths */
export const CODE_TAIL_MIDDLE = '∕';

export interface EqualsQuery extends ParsedQuery {
  kind: QueryKind.EQUALS;
  raw_q: string;
}

export function isFramedEqualsQuery(q: string): boolean {
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes('@')) {
    return false;
  }
  
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)(=)?(\d*)$/);
  if (!match) {
    return false;
  }
  
  const target = match[3] || '';
  if (!target) {
    return false;
  }
  
  const left_code = match[1] || '';
  const right_code = match[5] || '';
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  
  // Right equal with multi-char target or single char with left code
  if (right_equal && target.length >= 2) {
    return true;
  }
  if (right_equal && left_code && target.length === 1) {
    return true;
  }
  // Inner equal cases
  if (inner_equal && left_code && right_code) {
    return true;
  }
  if (inner_equal && left_code && !right_equal) {
    return true;
  }
  if (inner_equal && !left_code && !right_equal && target.length >= 2) {
    return true;
  }
  
  return false;
}
