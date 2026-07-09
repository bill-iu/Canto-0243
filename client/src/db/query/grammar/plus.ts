/** Port of query_grammar/plus. */
import { QueryKind } from '../../query-kind.ts';
import type { LiteralRefQuery, PlusAnchorQuery } from '../../query-types.ts';

/** Port of plus.parse_at_tail_query — 碼＋@＋尾字（23@手） */
export function parseAtTailQuery(q: string): LiteralRefQuery | null {
  const m = q.match(/^(\d+)@([\u4e00-\u9fff])$/);
  if (!m) {
    return null;
  }
  const code_digits = m[1]!;
  return {
    kind: QueryKind.LITERAL_REF,
    raw_q: q,
    code_digits,
    literal_char: m[2]!,
    width: code_digits.length,
  };
}

/** Port of plus.parse_plus_anchor_query — slot connector is `+` (Python CODE_TAIL_MIDDLE) */
export function parsePlusAnchorQuery(q: string): PlusAnchorQuery | null {
  if (!q || !q.includes('+') || q.includes('@')) {
    return null;
  }

  const base = (
    fields: Omit<PlusAnchorQuery, 'kind' | 'raw_q'>,
  ): PlusAnchorQuery => ({
    kind: QueryKind.PLUS_ANCHOR,
    raw_q: q,
    ...fields,
  });

  let m = q.match(/^\+([\u4e00-\u9fff])(=)?(\d+)$/);
  if (m) {
    const anchor = m[1]!;
    const right = m[3]!;
    const width = 1 + right.length;
    return base({
      width,
      anchor_pos: 0,
      anchor,
      constraint: m[2] ? 'final' : 'literal',
      code_slots: [...right].map((d, i) => [1 + i, d] as [number, string]),
    });
  }

  m = q.match(/^(\d+)\+([\u4e00-\u9fff])(=)?(\d+)$/);
  if (m) {
    const left = m[1]!;
    const anchor = m[2]!;
    const right = m[4]!;
    const anchorPos = left.length;
    const width = left.length + 1 + right.length;
    return base({
      width,
      anchor_pos: anchorPos,
      anchor,
      constraint: m[3] ? 'final' : 'literal',
      code_slots: [
        ...[...left].map((d, i) => [i, d] as [number, string]),
        ...[...right].map((d, i) => [anchorPos + 1 + i, d] as [number, string]),
      ],
    });
  }

  m = q.match(/^(\d+)\+([\u4e00-\u9fff])(=)?$/);
  if (m) {
    const code = m[1]!;
    const anchor = m[2]!;
    const width = code.length + 1;
    return base({
      width,
      anchor_pos: width - 1,
      anchor,
      constraint: m[3] ? 'final' : 'literal',
      code_slots: [...code].map((d, i) => [i, d] as [number, string]),
      code_prefix: code,
    });
  }

  m = q.match(/^(\d+)\+=([\u4e00-\u9fff])$/);
  if (m) {
    const code = m[1]!;
    const anchor = m[2]!;
    const width = code.length + 1;
    return base({
      width,
      anchor_pos: width - 1,
      anchor,
      constraint: 'initial',
      code_slots: [...code].map((d, i) => [i, d] as [number, string]),
      code_prefix: code,
    });
  }

  return null;
}
