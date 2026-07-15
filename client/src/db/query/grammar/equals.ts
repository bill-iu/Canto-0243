/**
 * Equals grammar — framed equals + MatchSpec (port of query_grammar/equals.py).
 */
import { QueryKind } from '../../query-kind.ts';
import type { ParsedQuery } from '../../query-types.ts';
import {
  attachEqualsSpan,
  createMatchSpec,
  type EqualsSpan,
  type MatchSpec,
} from '../../position-match/spec.ts';
import { CODE_TAIL_MIDDLE } from './shared.ts';

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

  if (right_equal && target.length >= 2) {
    return true;
  }
  if (right_equal && left_code && target.length === 1) {
    return true;
  }
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

/** Port of build_equals_match_spec — string → MatchSpec helper. */
export function buildEqualsMatchSpec(q: string): MatchSpec | null {
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)?(=)?(\d*)$/);
  if (!match) {
    return null;
  }

  const target_str = match[3] || '';
  if (!target_str) {
    return null;
  }

  const left_code = match[1] || '';
  const right_code = match[5] || '';
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  const target_length = target_str.length;
  const expected_length = left_code.length + right_code.length || target_length;
  const start_pos = Math.max(0, left_code.length - target_length);
  const full_code = left_code + right_code;

  const span: EqualsSpan = {
    ref_literal: target_str,
    start_pos,
    dimension: right_equal ? 'final' : 'initial',
    phoneme_anchor_only: Boolean(left_code && (right_code || inner_equal)),
    whole_word: start_pos === 0 && target_length === expected_length,
  };

  const spec = createMatchSpec(expected_length, {
    slots: [...full_code].map((d, i) => ({
      pos: i,
      kind: 'code_digit' as const,
      value: d,
    })),
  });
  attachEqualsSpan(spec, span);
  return spec;
}

/** ParsedQuery → MatchSpec for EQUALS. */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind !== QueryKind.EQUALS) {
    return null;
  }
  return buildEqualsMatchSpec((parsed as EqualsQuery).raw_q);
}
