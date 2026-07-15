/**
 * Port of query_grammar/rhyme (partial + anchors + double wild + code-ref).
 *
 * ponytail: 300-line limit exemption — rhyme family parse+toMatchSpec locality
 */
import { buildMaskFromSlots, isWildcardChar } from './mask.ts';
import {
  createMatchSpec,
  type MatchSpec,
} from '../../position-match/spec.ts';
import { QueryKind } from '../../query-kind.ts';
import type {
  CodeRefMiddleRhymeQuery,
  ParsedQuery,
  PartialInitialMaskQuery,
  PartialRhymeMaskQuery,
  RhymeAnchorQuery,
  TripleRhymeAnchorQuery,
} from '../../query-types.ts';
import { CODE_TAIL_MIDDLE } from './shared.ts';
import { isFramedEqualsQuery } from './equals.ts';

/** Port of rhyme.parse_code_ref_rhyme_contradiction_hint */
export function parseCodeRefRhymeContradictionHint(q: string): string | null {
  const m = q.match(/^([?_%]+)(\d+)([\u4e00-\u9fff])([?_%])$/);
  if (m && !q.includes('=')) {
    return `碼位同參考字「${m[3]}」衝突：請改用 \`?${m[2]}${m[3]}=?\` 標中格同韻。`;
  }
  return null;
}

/** Port of rhyme.parse_code_ref_middle_rhyme_query */
export function parseCodeRefMiddleRhymeQuery(q: string): CodeRefMiddleRhymeQuery | null {
  const m = q.match(/^([?_%]+)(\d+)([\u4e00-\u9fff])=\?$/);
  if (!m) {
    return null;
  }
  const leading = m[1]!;
  const digits = m[2]!;
  const anchor = m[3]!;
  const width = leading.length + digits.length + 1;
  const anchorPos = leading.length + digits.length - 1;
  const slots: CodeRefMiddleRhymeQuery['slots'] = [];
  for (let i = 0; i < digits.length; i++) {
    slots.push({ pos: leading.length + i, kind: 'code_digit', value: digits[i] });
  }
  slots.push({ pos: anchorPos, kind: 'final_anchor', value: anchor });
  return {
    kind: QueryKind.CODE_REF_MIDDLE_RHYME,
    raw_q: q,
    width,
    anchor,
    anchor_pos: anchorPos,
    leading,
    digits,
    slots,
  };
}

/** Port of rhyme.parse_double_wildcard_rhyme_query */
export function parseDoubleWildcardRhymeQuery(q: string): RhymeAnchorQuery | null {
  const m = q.match(/^([?_%])\+([\u4e00-\u9fff])=$/);
  if (!m) {
    return null;
  }
  return {
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    constraint: 'final',
    anchor: m[2]!,
    anchor_pos: 1,
    slots: m[1]!,
    width: 2,
  };
}

/** Port of rhyme.parse_double_wildcard_initial_query */
export function parseDoubleWildcardInitialQuery(q: string): RhymeAnchorQuery | null {
  const m = q.match(/^([?_%])\+=([\u4e00-\u9fff])$/);
  if (!m) {
    return null;
  }
  return {
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    constraint: 'initial',
    anchor: m[2]!,
    anchor_pos: 1,
    slots: m[1]!,
    width: 2,
  };
}

/** Port of rhyme.parse_triple_rhyme_anchor_query */
export function parseTripleRhymeAnchorQuery(q: string): TripleRhymeAnchorQuery | null {
  if (!q || q.includes('@') || isFramedEqualsQuery(q)) {
    return null;
  }

  let m = q.match(/^(\?\+)([\u4e00-\u9fff])=\?$/);
  if (m) {
    return {
      kind: QueryKind.TRIPLE_RHYME_ANCHOR,
      raw_q: q,
      anchor: m[2]!,
      anchor_pos: 1,
      width: 3,
      leading_slots: m[1]!,
      constraint: 'final',
    };
  }

  if (q.includes('+') || q.includes(CODE_TAIL_MIDDLE)) {
    return null;
  }

  m = q.match(/^([0-9_?%]+)([\u4e00-\u9fff])=\?$/);
  if (!m) {
    return null;
  }
  const leading = m[1]!;
  const anchor = m[2]!;
  if (![...leading].some((c) => isWildcardChar(c))) {
    return null;
  }
  if (/\d/.test(leading)) {
    return null;
  }
  const anchorPos = leading.length;
  return {
    kind: QueryKind.TRIPLE_RHYME_ANCHOR,
    raw_q: q,
    anchor,
    anchor_pos: anchorPos,
    width: anchorPos + 2,
    leading_slots: leading,
    constraint: 'final',
  };
}

/** Port of rhyme.normalize_partial_rhyme_mask_query */
function normalizePartialRhymeMaskQuery(q: string): string {
  const m = q.match(/^([\u4e00-\u9fff]{3})=\?$/);
  if (m) {
    return `${m[1]}?=`;
  }
  return q;
}

/** Port of rhyme.parse_partial_rhyme_mask_query */
export function parsePartialRhymeMaskQuery(q: string): PartialRhymeMaskQuery | null {
  const nq = normalizePartialRhymeMaskQuery(q);
  const m = nq.match(/^([\u4e00-\u9fff?]{4})=$/);
  if (!m) {
    return null;
  }
  const pattern = m[1]!;
  if (!pattern.includes('?') || pattern.split('').every((ch) => ch === '?')) {
    return null;
  }
  if (pattern.startsWith('?') && /^\?[\u4e00-\u9fff]{3}$/.test(pattern)) {
    return null;
  }
  const anchors: Array<[number, string]> = [];
  for (let pos = 0; pos < pattern.length; pos++) {
    const ch = pattern[pos]!;
    if (ch !== '?') {
      anchors.push([pos, ch]);
    }
  }
  if (!anchors.length) {
    return null;
  }
  return {
    kind: QueryKind.PARTIAL_RHYME_MASK,
    raw_q: q,
    pattern,
    width: 4,
    anchors,
  };
}

/** Port of rhyme.parse_partial_initial_mask_query */
export function parsePartialInitialMaskQuery(q: string): PartialInitialMaskQuery | null {
  const m = q.match(/^=([\u4e00-\u9fff?]{4})$/);
  if (!m) {
    return null;
  }
  const pattern = m[1]!;
  if (!pattern.includes('?') || pattern.split('').every((ch) => ch === '?')) {
    return null;
  }
  if (pattern.startsWith('?') && /^\?[\u4e00-\u9fff]{3}$/.test(pattern)) {
    return null;
  }
  const anchors: Array<[number, string]> = [];
  for (let pos = 0; pos < pattern.length; pos++) {
    const ch = pattern[pos]!;
    if (ch !== '?') {
      anchors.push([pos, ch]);
    }
  }
  if (!anchors.length) {
    return null;
  }
  return {
    kind: QueryKind.PARTIAL_INITIAL_MASK,
    raw_q: q,
    pattern,
    width: 4,
    anchors,
  };
}

/** Port of query_grammar/rhyme.parse_rhyme_anchor_query (P1 subset) */
export function parseRhymeAnchorQuery(q: string): RhymeAnchorQuery | null {
  if (!q || q.includes(CODE_TAIL_MIDDLE) || q.includes('+') || q.includes('@') || isFramedEqualsQuery(q)) {
    return null;
  }
  if (parseDoubleWildcardRhymeQuery(q) || parseDoubleWildcardInitialQuery(q)) {
    return null;
  }

  const base = (fields: Omit<RhymeAnchorQuery, 'kind' | 'raw_q'>): RhymeAnchorQuery => ({
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    ...fields,
  });

  let m = q.match(/^([\u4e00-\u9fff])=$/);
  if (m) {
    return base({
      constraint: 'final',
      anchor: m[1]!,
      anchor_pos: 0,
      slots: '',
      width: 1,
    });
  }

  m = q.match(/^=([\u4e00-\u9fff])$/);
  if (m) {
    return base({
      constraint: 'initial',
      anchor: m[1]!,
      anchor_pos: 0,
      slots: '',
      width: 1,
    });
  }

  m = q.match(/^([0-9_?%]+)([\u4e00-\u9fff])=$/);
  if (m) {
    const slots = m[1]!;
    return base({
      constraint: 'final',
      anchor: m[2]!,
      anchor_pos: slots.length,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^([\u4e00-\u9fff])=([0-9_?%]+)$/);
  if (m) {
    const slots = m[2]!;
    return base({
      constraint: 'final',
      anchor: m[1]!,
      anchor_pos: 0,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^=([\u4e00-\u9fff])([0-9_?%]+)$/);
  if (m) {
    const slots = m[2]!;
    return base({
      constraint: 'initial',
      anchor: m[1]!,
      anchor_pos: 0,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^([0-9_?%]+)=([\u4e00-\u9fff])$/);
  if (m) {
    const slots = m[1]!;
    return base({
      constraint: 'initial',
      anchor: m[2]!,
      anchor_pos: slots.length,
      slots,
      width: slots.length + 1,
    });
  }

  return null;
}

/** Port of query_grammar.rhyme.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind === QueryKind.PARTIAL_RHYME_MASK) {
    const q = parsed as PartialRhymeMaskQuery;
    const spec = createMatchSpec(q.width, { mask: q.pattern });
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.partial_rhyme_mask = true;
    if (!spec.slots) {
      spec.slots = [];
    }
    for (const [pos, ch] of q.anchors) {
      spec.slots.push({ pos, kind: 'final_anchor', value: ch });
    }
    return spec;
  }
  if (parsed.kind === QueryKind.PARTIAL_INITIAL_MASK) {
    const q = parsed as PartialInitialMaskQuery;
    const spec = createMatchSpec(q.width, { mask: q.pattern });
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.partial_initial_mask = true;
    if (!spec.slots) {
      spec.slots = [];
    }
    for (const [pos, ch] of q.anchors) {
      spec.slots.push({ pos, kind: 'initial_anchor', value: ch });
    }
    return spec;
  }
  if (parsed.kind === QueryKind.CODE_REF_MIDDLE_RHYME) {
    const q = parsed as CodeRefMiddleRhymeQuery;
    const spec = createMatchSpec(q.width);
    spec.mask = '?'.repeat(q.width);
    if (!spec.slots) {
      spec.slots = [];
    }
    for (const slot of q.slots) {
      spec.slots.push({
        pos: slot.pos,
        kind: slot.kind as import('../../position-match/spec.ts').ConstraintKind,
        value: slot.value,
      });
    }
    return spec;
  }
  if (parsed.kind === QueryKind.RHYME_ANCHOR) {
    const q = parsed as RhymeAnchorQuery;
    const spec = createMatchSpec(q.width);
    const kind = q.constraint === 'final' ? 'final_anchor' : 'initial_anchor';
    if (!spec.slots) {
      spec.slots = [];
    }
    spec.slots.push({ pos: q.anchor_pos, kind, value: q.anchor });
    spec.mask = buildMaskFromSlots(q.slots, q.width, q.anchor_pos);
    return spec;
  }
  if (parsed.kind === QueryKind.TRIPLE_RHYME_ANCHOR) {
    const q = parsed as TripleRhymeAnchorQuery;
    const spec = createMatchSpec(q.width);
    if (!spec.slots) {
      spec.slots = [];
    }
    spec.slots.push({ pos: q.anchor_pos, kind: 'final_anchor', value: q.anchor });
    spec.mask = '?'.repeat(q.width);
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.triple_rhyme_anchor = true;
    return spec;
  }
  return null;
}
