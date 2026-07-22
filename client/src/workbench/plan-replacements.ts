import { queryRows, type DatabaseBackend } from '../db/database-backend.ts';
import { executeMatchSpecPage } from '../db/position-match/engine.ts';
import type { WordRow } from '../db/position-match/word-row.ts';
import { projectRelationPool } from '../db/relation-pool/index.ts';
import { buildMatchSpec } from './build-match-spec.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from './contracts.ts';
import { groupCandidates, type GroupPoolInput } from './group-candidates.ts';
import { shouldSkipCandidateQuery } from './limits.ts';
import { relaxationVariants } from './relaxation-advisor.ts';

type PlannerDeps = {
  executePage?: typeof executeMatchSpecPage;
  projectRelations?: typeof projectRelationPool;
};

async function loadRelationRows(
  db: DatabaseBackend,
  width: number,
  pool: GroupPoolInput,
): Promise<WordRow[]> {
  const literals = [...new Set([
    ...(pool?.syns ?? []).map((item) => item.char),
    ...(pool?.semantic ?? []).map((item) => item.char),
  ].filter(Boolean))];
  const rows: WordRow[] = [];
  for (let start = 0; start < literals.length; start += 499) {
    const chunk = literals.slice(start, start + 499);
    const placeholders = chunk.map(() => '?').join(',');
    rows.push(...await queryRows(
      db,
      `SELECT char, jyutping, code FROM words WHERE length = ? AND char IN (${placeholders}) ORDER BY char, code, jyutping`,
      [width, ...chunk],
    ));
  }
  return rows;
}

function prependDistinct(rows: WordRow[], priorityRows: WordRow[]): WordRow[] {
  const seen = new Set<string>();
  return [...priorityRows, ...rows].filter((row) => {
    const key = [row.char, row.jyutping, row.code].map((value) => String(value ?? '')).join('\0');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Thin orchestrator (L4): execute → group → optional one relaxation probe. */
export async function planReplacements(
  plan: ReplacementPlanV1,
  db: DatabaseBackend,
  deps: PlannerDeps = {},
): Promise<WorkbenchCandidateResponse> {
  // ADR-0069: structural empty when wider than observed lexicon max word length.
  if (shouldSkipCandidateQuery(plan.width)) {
    return {
      version: 1,
      selectionVersion: plan.selectionVersion,
      exact: { direct_syn: [], semantic_related: [], sound_only: [] },
      total: 0,
      engineTotal: 0,
      relaxation: null,
    };
  }
  const executePage = deps.executePage ?? executeMatchSpecPage;
  const project = deps.projectRelations ?? projectRelationPool;
  const pool = plan.semanticIntent !== 'off' && plan.semanticSeed
    ? await project(db, plan.semanticSeed) : null;
  const offset = plan.offset ?? 0;
  const run = (variant: ReplacementPlanV1) => executePage(buildMatchSpec(variant), {
    db,
    mode: variant.mode,
    limit: variant.limit,
    offset: variant.offset ?? 0,
    code: null,
  });
  const page = await run(plan);
  const rows = pool && !plan.slots.length && offset === 0
    ? prependDistinct(page.rows, await loadRelationRows(db, plan.width, pool))
    : page.rows;
  const exact = groupCandidates(plan, rows, pool);
  let relaxation = null;
  if (offset === 0 && ![...exact.direct_syn, ...exact.semantic_related, ...exact.sound_only].length) {
    for (const variant of relaxationVariants(plan)) {
      const probed = await run({ ...variant.plan, offset: 0, limit: variant.plan.limit });
      const count = variant.plan.semanticIntent === 'direct_only'
        ? probed.rows.filter((row) => (pool?.syns ?? []).some((item) => item.char === String(row.char ?? ''))).length
        : probed.total;
      if (count < 1) continue;
      relaxation = { ...variant, candidateCount: count };
      break;
    }
  }
  return {
    version: 1,
    selectionVersion: plan.selectionVersion,
    exact,
    total: page.total,
    engineTotal: page.total,
    relaxation,
  };
}

/** @deprecated use planReplacements */
export const planPwaReplacements = planReplacements;
