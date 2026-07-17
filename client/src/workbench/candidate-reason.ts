import type {
  CandidateGroup,
  CandidateReason,
  ReplacementPlanV1,
} from './contracts.ts';

const NORMALIZED_DIGIT: Record<string, string> = { '1': '3', '6': '2', '7': '3', '8': '4' };

export function candidateReasons(
  plan: ReplacementPlanV1,
  code: string,
  group: CandidateGroup,
  relationSource?: string,
): CandidateReason[] {
  const reasons: CandidateReason[] = [];
  for (const slot of plan.slots) {
    if (slot.kind === 'code_digit') {
      const expected = NORMALIZED_DIGIT[slot.digit ?? ''] ?? slot.digit;
      reasons.push({
        kind: code[slot.pos] === expected ? 'tone_exact' : 'tone_loose',
        positions: [slot.pos],
      });
    } else if (slot.kind === 'literal_char') {
      reasons.push({ kind: 'literal_match', positions: [slot.pos] });
    } else if (slot.kind === 'final_anchor') {
      reasons.push({ kind: 'same_final', positions: [slot.pos] });
    } else if (slot.kind === 'initial_anchor') {
      reasons.push({ kind: 'same_initial', positions: [slot.pos] });
    } else if (slot.kind === 'tone_class') {
      reasons.push({ kind: 'tone_exact', positions: [slot.pos] });
    }
  }
  if (group === 'direct_syn') reasons.push({ kind: 'direct_syn', positions: [], source: relationSource });
  if (group === 'semantic_related') reasons.push({ kind: 'semantic_related', positions: [], source: relationSource });
  reasons.push({ kind: 'frequency_rank', positions: [] });
  return reasons;
}
