/** Port of app/services/query_grammar/equals.build_equals_match_spec */
import {
  attachEqualsSpan,
  createMatchSpec,
  type EqualsSpan,
  type MatchSpec,
} from './spec.ts';

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
    code_prefix: full_code || undefined,
  });
  attachEqualsSpan(spec, span);
  return spec;
}
