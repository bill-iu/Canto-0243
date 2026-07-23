import type { WordRow } from '../db/position-match/word-row.ts';
import { candidateReasons } from './candidate-reason.ts';
import { compareSoundOnlyCandidates, relationIndex } from './candidate-rank.ts';
import type {
  CandidateGroup,
  CandidateGroups,
  ReplacementPlanV1,
  WorkbenchCandidate,
} from './contracts.ts';

/** Minimal pool surface for grouping (full RelationPoolSnapshot is fine). */
export type GroupPoolInput = {
  syns?: Array<{ char: string; source?: string }>;
  semantic?: Array<{ char: string; source?: string }>;
} | null;

function compareRelationCandidates(a: WorkbenchCandidate, b: WorkbenchCandidate): number {
  return a.sourceRank - b.sourceRank
    || a.literal.localeCompare(b.literal)
    || a.jyutping.localeCompare(b.jyutping);
}

/** rows + optional relation pool → CandidateGroups（L2）。 */
export function groupCandidates(
  plan: ReplacementPlanV1,
  rows: WordRow[],
  pool: GroupPoolInput,
): CandidateGroups {
  const direct = relationIndex(pool?.syns ?? []);
  const semantic = relationIndex(pool?.semantic ?? []);
  const groups: CandidateGroups = { direct_syn: [], semantic_related: [], sound_only: [] };
  rows.forEach((row, rowRank) => {
    const literal = String(row.char ?? '');
    if (!literal) return;
    let group: CandidateGroup = direct.has(literal) ? 'direct_syn'
      : semantic.has(literal) ? 'semantic_related' : 'sound_only';
    const relation = group === 'direct_syn' ? direct.get(literal) : semantic.get(literal);
    if (plan.semanticIntent === 'direct_only' && group !== 'direct_syn') return;
    if (plan.semanticIntent === 'off') group = 'sound_only';
    const code = String(row.code ?? '');
    const candidate: WorkbenchCandidate = {
      literal,
      jyutping: String(row.jyutping ?? ''),
      code,
      group,
      reasons: candidateReasons(plan, code, group, relation?.source),
      sourceRank: plan.semanticIntent === 'off' ? rowRank : relation?.rank ?? rowRank,
    };
    groups[group].push(candidate);
  });
  groups.direct_syn.sort(compareRelationCandidates);
  groups.semantic_related.sort(compareRelationCandidates);
  groups.sound_only.sort(compareSoundOnlyCandidates);
  return groups;
}

/** Literals only per group — for L2 fixture parity without reason noise. */
export function groupLiterals(groups: CandidateGroups): Record<CandidateGroup, string[]> {
  return {
    direct_syn: groups.direct_syn.map((c) => c.literal),
    semantic_related: groups.semantic_related.map((c) => c.literal),
    sound_only: groups.sound_only.map((c) => c.literal),
  };
}
