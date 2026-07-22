import { queryRows, type DatabaseBackend } from '../db/database-backend.ts';
import { executeMatchSpecPage } from '../db/position-match/engine.ts';
import type { WordRow } from '../db/position-match/word-row.ts';
import { projectRelationPool } from '../db/relation-pool/index.ts';
import { buildMatchSpec } from './build-match-spec.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from './contracts.ts';
import { groupCandidates, type GroupPoolInput } from './group-candidates.ts';
import { shouldSkipCandidateQuery } from './limits.ts';
import { relaxationVariants } from './relaxation-advisor.ts';
import { throwIfSearchCancelled, type ShouldCancel } from '../db/search-cancel.ts';

export type PlannerDeps = {
  executePage?: typeof executeMatchSpecPage;
  projectRelations?: (db: DatabaseBackend, seed: string) => Promise<GroupPoolInput>;
  shouldCancel?: ShouldCancel;
};

type CandidateHandle = string;

export type ReplacementSnapshot = Readonly<{
  candidates: readonly CandidateHandle[];
  pool: GroupPoolInput;
  relaxation: WorkbenchCandidateResponse['relaxation'];
}>;

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
    const key = String(row.char ?? '');
    if (!key) return false;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function compactDistinct(rows: WordRow[]): CandidateHandle[] {
  const seen = new Set<string>();
  const handles: CandidateHandle[] = [];
  for (const row of rows) {
    const literal = String(row.char ?? '');
    if (!literal || seen.has(literal)) continue;
    seen.add(literal);
    handles.push(`${literal}\0${String(row.jyutping ?? '')}\0${String(row.code ?? '')}`);
  }
  return handles;
}

function materialize(handles: readonly CandidateHandle[]): WordRow[] {
  return handles.map((handle) => {
    const [char = '', jyutping = '', code = ''] = handle.split('\0', 3);
    return { char, jyutping, code };
  });
}

function snapshotHasCandidates(
  plan: ReplacementPlanV1,
  handles: readonly CandidateHandle[],
  pool: GroupPoolInput,
): boolean {
  if (plan.semanticIntent !== 'direct_only') return handles.length > 0;
  const direct = new Set((pool?.syns ?? []).map((item) => item.char));
  return handles.some((handle) => direct.has(handle.slice(0, handle.indexOf('\0'))));
}

/** Build one immutable canonical pool; paging and draft version are projections. */
export async function buildReplacementSnapshot(
  plan: ReplacementPlanV1,
  db: DatabaseBackend,
  deps: PlannerDeps = {},
): Promise<ReplacementSnapshot> {
  if (shouldSkipCandidateQuery(plan.width)) {
    return { candidates: [], pool: null, relaxation: null };
  }
  const executePage = deps.executePage ?? executeMatchSpecPage;
  const project = deps.projectRelations ?? projectRelationPool;
  const pool = plan.semanticIntent !== 'off' && plan.semanticSeed
    ? await project(db, plan.semanticSeed) : null;
  const runFull = (variant: ReplacementPlanV1) => {
    const spec = buildMatchSpec(variant);
    spec.extra = { ...(spec.extra ?? {}), workbench_full_bucket_scan: true };
    return executePage(spec, {
      db,
      mode: variant.mode,
      limit: 1_000_000,
      offset: 0,
      code: null,
      shouldCancel: deps.shouldCancel,
    });
  };
  const priorityRows = pool && !plan.slots.length
    ? await loadRelationRows(db, plan.width, pool)
    : [];
  const raw = await runFull(plan);
  throwIfSearchCancelled(deps.shouldCancel);
  const candidates = compactDistinct(
    priorityRows.length ? prependDistinct(raw.rows, priorityRows) : raw.rows,
  );
  let relaxation = null;
  if (!snapshotHasCandidates(plan, candidates, pool)) {
    for (const variant of relaxationVariants(plan)) {
      throwIfSearchCancelled(deps.shouldCancel);
      const probed = compactDistinct((await runFull(variant.plan)).rows);
      const count = variant.plan.semanticIntent === 'direct_only'
        ? groupCandidates(variant.plan, materialize(probed), pool).direct_syn.length
        : probed.length;
      if (count < 1) continue;
      relaxation = { ...variant, candidateCount: count };
      break;
    }
  }
  return { candidates, pool, relaxation };
}

/** Materialize one transport page from a completed snapshot. */
export function pageReplacementSnapshot(
  plan: ReplacementPlanV1,
  snapshot: ReplacementSnapshot,
): WorkbenchCandidateResponse {
  const offset = plan.offset ?? 0;
  const rows = materialize(snapshot.candidates.slice(offset, offset + plan.limit));
  const total = snapshot.candidates.length;
  const relaxation = snapshot.relaxation == null ? null : {
    ...snapshot.relaxation,
    plan: { ...snapshot.relaxation.plan, selectionVersion: plan.selectionVersion },
  };
  return {
    version: 1,
    selectionVersion: plan.selectionVersion,
    exact: groupCandidates(plan, rows, snapshot.pool),
    total,
    engineTotal: total,
    relaxation: offset === 0 ? relaxation : null,
  };
}

/** Stateless compatibility entry; adapters should retain buildReplacementSnapshot(). */
export async function planReplacements(
  plan: ReplacementPlanV1,
  db: DatabaseBackend,
  deps: PlannerDeps = {},
): Promise<WorkbenchCandidateResponse> {
  return pageReplacementSnapshot(plan, await buildReplacementSnapshot(plan, db, deps));
}

/** @deprecated use planReplacements */
export const planPwaReplacements = planReplacements;
