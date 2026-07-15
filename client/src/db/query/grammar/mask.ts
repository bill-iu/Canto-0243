/**
 * Port of query_grammar/mask.py — mask helpers + MatchSpec.
 *
 * Callers in position-match may still import via mask-grammar.ts thin re-export.
 */
import { QueryKind } from '../../query-kind.ts';
import type { MaskQuery, ParsedQuery } from '../../query-types.ts';
import {
  createMatchSpec,
  type MatchSpec,
} from '../../position-match/spec.ts';
import { CODE_TAIL_MIDDLE } from './shared.ts';

const WILDCARD_CHARS = new Set(['?', '_', '%']);

export function isWildcardChar(ch: string): boolean {
  return WILDCARD_CHARS.has(ch);
}

export function parseMaskQuery(mask: string): {
  width: number;
  requiredCodes: Array<string | null>;
  literalPositions: Array<[number, string]>;
} {
  const requiredCodes: Array<string | null> = Array(mask.length).fill(null);
  const literalPositions: Array<[number, string]> = [];
  for (let idx = 0; idx < mask.length; idx++) {
    const ch = mask[idx]!;
    if (isWildcardChar(ch)) {
      continue;
    }
    if (/\d/.test(ch)) {
      requiredCodes[idx] = ch;
      continue;
    }
    literalPositions.push([idx, ch]);
  }
  return { width: mask.length, requiredCodes, literalPositions };
}

export function buildMaskFromSlots(slots: string, width: number, anchorPos: number): string {
  const chars = Array(width).fill('?');
  if (anchorPos === 0) {
    for (let i = 0; i < slots.length; i++) {
      chars[i + 1] = slots[i]!;
    }
  } else {
    for (let i = 0; i < slots.length; i++) {
      chars[i] = slots[i]!;
    }
  }
  return chars.join('');
}

/** Port of query_grammar/mask.looks_like_mask_query (shape only; parse chain gates elsewhere). */
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

/** Port of query_grammar.mask.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind !== QueryKind.MASK) {
    return null;
  }
  const q = parsed as MaskQuery;
  const { literalPositions } = parseMaskQuery(q.raw_q);
  const spec = createMatchSpec(q.raw_q.length, {
    literal_priority: true,
    mask: q.raw_q,
  });
  if (!spec.slots) {
    spec.slots = [];
  }
  for (let i = 0; i < q.raw_q.length; i++) {
    const ch = q.raw_q[i]!;
    if (/\d/.test(ch)) {
      spec.slots.push({ pos: i, kind: 'code_digit', value: ch });
    }
  }
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra.literal_positions = literalPositions;
  return spec;
}
