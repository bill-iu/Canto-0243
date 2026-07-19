import type { DatabaseBackend } from '../db/database-backend.ts';
import { executeMatchSpec } from '../db/position-match/engine.ts';
import { attachEqualsSpan, type MatchSpec, type SlotConstraint } from '../db/position-match/spec.ts';
import type { WordRow } from '../db/position-match/word-row.ts';
import { projectRelationPool } from '../db/relation-pool-projection.ts';
import type { RelationPoolSnapshot } from '../db/relation-pool-snapshot.ts';
import { candidateReasons } from './candidate-reason.ts';
import { relationIndex } from './candidate-rank.ts';
import type {
  CandidateGroup,
  CandidateGroups,
  ReplacementPlanV1,
  WorkbenchCandidate,
  WorkbenchCandidateResponse,
} from './contracts.ts';
import { relaxationVariants } from './relaxation-advisor.ts';

type PlannerDeps = {
  execute?: typeof executeMatchSpec;
  projectRelations?: typeof projectRelationPool;
};

export function buildPwaMatchSpec(plan: ReplacementPlanV1): MatchSpec {
  const mask = Array.from({ length: plan.width }, () => '?');
  const slots: SlotConstraint[] = plan.slots.map((item) => {
    const value = item.kind === 'code_digit' ? item.digit
      : item.kind === 'literal_char' ? item.literal
        : item.kind === 'tone_class' ? item.toneClass
          : item.ref;
    if (item.kind === 'literal_char' && item.literal) mask[item.pos] = item.literal;
    return { pos: item.pos, kind: item.kind, value };
  });
  const spec: MatchSpec = { width: plan.width, slots, mask: mask.join(''), extra: {} };
  for (const [kind, dimension] of [['final_anchor', 'final'], ['initial_anchor', 'initial']] as const) {
    const anchorItems = plan.slots.filter((slot) => slot.kind === kind).sort((a, b) => a.pos - b.pos);
    const anchors = slots.filter((slot) => slot.kind === kind).sort((a, b) => a.pos - b.pos);
    const positions = anchors.map((slot) => slot.pos);
    const contiguous = positions.length >= 2
      && positions.every((pos, index) => index === 0 || pos === positions[index - 1]! + 1);
    if (!contiguous || anchorItems.some((slot) => !slot.refJyutping)) continue;
    spec.slots = slots.filter((slot) => slot.kind !== kind);
    attachEqualsSpan(spec, {
      ref_literal: anchors.map((slot) => String(slot.value ?? '')).join(''),
      ref_jyutping: anchorItems
        .map((slot) => slot.refJyutping ?? '')
        .join(' ') || undefined,
      start_pos: positions[0]!,
      dimension,
      phoneme_anchor_only: true,
      whole_word: positions[0] === 0 && positions.length === plan.width,
    });
    if (positions[0]! > 0 && positions[positions.length - 1] === plan.width - 1) {
      spec.extra!.prefix_wildcard_equals = true;
    }
    break;
  }
  return spec;
}

function groupRows(
  plan: ReplacementPlanV1,
  rows: WordRow[],
  pool: RelationPoolSnapshot | null,
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
  for (const values of Object.values(groups) as WorkbenchCandidate[][]) {
    values.sort((a, b) => a.sourceRank - b.sourceRank || a.literal.localeCompare(b.literal) || a.jyutping.localeCompare(b.jyutping));
  }
  return groups;
}

export async function planPwaReplacements(
  plan: ReplacementPlanV1,
  db: DatabaseBackend,
  deps: PlannerDeps = {},
): Promise<WorkbenchCandidateResponse> {
  const execute = deps.execute ?? executeMatchSpec;
  const project = deps.projectRelations ?? projectRelationPool;
  const pool = plan.semanticIntent !== 'off' && plan.semanticSeed
    ? await project(db, plan.semanticSeed) : null;
  const run = (variant: ReplacementPlanV1) => execute(buildPwaMatchSpec(variant), {
    db,
    mode: variant.mode,
    limit: variant.limit,
    offset: 0,
    code: null,
  });
  const exact = groupRows(plan, await run(plan), pool);
  let relaxation = null;
  if (![...exact.direct_syn, ...exact.semantic_related, ...exact.sound_only].length) {
    for (const variant of relaxationVariants(plan)) {
      const rows = await run(variant.plan);
      const count = variant.plan.semanticIntent === 'direct_only'
        ? rows.filter((row) => (pool?.syns ?? []).some((item) => item.char === String(row.char ?? ''))).length
        : rows.length;
      if (count < 1) continue;
      relaxation = { ...variant, candidateCount: count };
      break;
    }
  }
  return { version: 1, selectionVersion: plan.selectionVersion, exact, relaxation };
}
