/** Port of query_grammar/plus. */
import { appendCodeDigitSlots } from '../../position-match/filters/f1-slot-code.ts';
import { createMatchSpec, type MatchSpec } from '../../position-match/spec.ts';
import { QueryKind } from '../../query-kind.ts';
import type {
  LiteralRefQuery,
  ParsedQuery,
  PlusAnchorQuery,
} from '../../query-types.ts';

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

  m = q.match(/^(\d+)\+[\^=]([\u4e00-\u9fff])$/);
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

/** Port of plus.mask_from_canonical_plus_query — `+香??` / `?+你?` → mask literal. */
const HEAD_LITERAL_MASK_RE = /^\+([\u4e00-\u9fff][0-9_?%]+)$/;
const MIDDLE_LITERAL_MASK_RE = /^([_?%])\+([\u4e00-\u9fff])([0-9_?%]*)$/;

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

/** Port of query_grammar.plus.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind === QueryKind.PLUS_ANCHOR) {
    const q = parsed as PlusAnchorQuery;
    const spec = createMatchSpec(q.width);
    spec.mask = '?'.repeat(q.width);
    if (!spec.slots) {
      spec.slots = [];
    }
    for (const [pos, d] of q.code_slots) {
      spec.slots.push({ pos, kind: 'code_digit', value: d });
    }
    if (!q.code_slots?.length && q.code_prefix) {
      appendCodeDigitSlots(spec, q.code_prefix);
    }
    if (q.constraint === 'literal') {
      spec.slots.push({ pos: q.anchor_pos, kind: 'literal_char', value: q.anchor });
      spec.mask = spec.mask.slice(0, q.anchor_pos) + q.anchor + spec.mask.slice(q.anchor_pos + 1);
      return spec;
    }
    if (q.constraint === 'final') {
      spec.slots.push({ pos: q.anchor_pos, kind: 'final_anchor', value: q.anchor });
      return spec;
    }
    if (q.constraint === 'initial') {
      spec.slots.push({ pos: q.anchor_pos, kind: 'initial_anchor', value: q.anchor });
    }
    return spec;
  }
  if (parsed.kind === QueryKind.LITERAL_REF) {
    const q = parsed as LiteralRefQuery;
    const spec = createMatchSpec(q.width);
    appendCodeDigitSlots(spec, q.code_digits);
    if (!spec.slots) {
      spec.slots = [];
    }
    spec.slots.push({ pos: q.width - 1, kind: 'literal_char', value: q.literal_char });
    spec.mask = '?'.repeat(q.width - 1) + q.literal_char;
    return spec;
  }
  return null;
}
