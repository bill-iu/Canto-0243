/** Port of query_grammar/heteronym. */
import { QueryKind } from '../../query-kind.ts';
import type { HeteronymCodeQuery, UnmatchedQuery } from '../../query-types.ts';

/** Port of heteronym.parse_heteronym_code_query */
export function parseHeteronymCodeQuery(q: string): HeteronymCodeQuery | UnmatchedQuery | null {
  if (!q || q.includes('$') || /[\u4e00-\u9fff]/.test(q)) {
    return null;
  }
  const m = q.match(/^([\d?]+)\/([\d?]+)$/);
  if (!m) {
    return null;
  }
  const left = m[1]!;
  const right = m[2]!;
  if (left.length !== right.length) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: '同音異讀查詢左右碼位模板須等長。',
    };
  }
  return {
    kind: QueryKind.HETERONYM_CODE,
    raw_q: q,
    left_template: left,
    right_template: right,
    width: left.length,
  };
}
