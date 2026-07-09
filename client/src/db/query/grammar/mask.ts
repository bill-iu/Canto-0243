/** Port of query_grammar/mask.looks_like_mask_query. */
import { isWildcardChar } from '../../position-match/mask-grammar.ts';
import { CODE_TAIL_MIDDLE } from './shared.ts';

export function looksLikeMaskQuery(q: string): boolean {
  if (!q || q.includes(CODE_TAIL_MIDDLE) || q.includes('@')) {
    return false;
  }
  if (!/^[0-9_?%\u4e00-\u9fff]+$/.test(q)) {
    return false;
  }
  const hasWild = [...q].some((c) => isWildcardChar(c));
  const hasDigit = /\d/.test(q);
  const hasCanto = [...q].some((c) => !/\d/.test(c) && !isWildcardChar(c));
  return hasWild || (hasDigit && hasCanto);
}
