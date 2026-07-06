/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { sortWordRows, literalPriorityCompare } from '../ranking.ts';
import { applyMatchSpec, filterHybridRefCandidates } from './filters.ts';
import { getCandidatesForLength, getLengthMaskCandidates } from './sources.ts';
import { getEqualsSpan, type MatchSpec } from './spec.ts';
import type { WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);

function shouldUseMaskCandidates(spec: MatchSpec): boolean {
  if (spec.extra?.partial_rhyme_mask || spec.extra?.partial_initial_mask) {
    return Boolean(spec.mask);
  }
  if (!spec.mask || spec.compound_kind || getEqualsSpan(spec)) {
    return false;
  }
  if (spec.literal_priority) {
    return true;
  }
  return (spec.slots ?? []).some(
    (s) => s.kind === 'final_anchor' || s.kind === 'initial_anchor',
  );
}

function specNeedsFullLengthBucket(spec: MatchSpec): boolean {
  return (spec.slots ?? []).some((s) => JYUTPING_LETTER_KINDS.has(s.kind));
}

export type ExecuteMatchSpecContext = {
  db: Database;
  mode: string;
  limit: number;
  offset: number;
  code?: string | null;
};

/** Filter all matching rows — port of PositionMatchEngine.match (no sort/page). */
export async function filterMatchSpecRows(
  spec: MatchSpec,
  ctx: Pick<ExecuteMatchSpecContext, 'db' | 'mode' | 'code'>,
): Promise<WordRow[]> {
  if (!spec || spec.width === 0) {
    return [];
  }
  if (getEqualsSpan(spec) || spec.compound_kind) {
    return applyMatchSpec(spec, [], ctx.db, ctx.mode);
  }
  if (spec.hybrid_ref_chars != null && spec.hybrid_ref_pos != null) {
    const [candidates] = await getCandidatesForLength(ctx.db, spec.width, {
      code: ctx.code ?? spec.code_prefix ?? null,
      mode: ctx.mode,
    });
    return filterHybridRefCandidates(candidates, spec, ctx.mode, ctx.db);
  }

  const hasPositionFilters =
    Boolean(spec.mask) ||
    (spec.slots ?? []).some(
      (s) =>
        s.kind === 'final_anchor' ||
        s.kind === 'initial_anchor' ||
        JYUTPING_LETTER_KINDS.has(s.kind),
    );
  if (!hasPositionFilters) {
    return [];
  }

  const code = ctx.code ?? spec.code_prefix ?? null;
  const [candidates] =
    shouldUseMaskCandidates(spec) && spec.mask
      ? await getLengthMaskCandidates(ctx.db, spec.width, spec.mask)
      : await getCandidatesForLength(ctx.db, spec.width, {
          code,
          mode: ctx.mode,
          unlimited: specNeedsFullLengthBucket(spec),
        });
  return applyMatchSpec(spec, candidates, ctx.db, ctx.mode);
}

async function executeDualPhonemeAnchorSpecs(spec: MatchSpec, ctx: ExecuteMatchSpecContext): Promise<WordRow[]> {
  const initialSpec = spec.extra?.dual_initial_spec;
  const finalSpec = spec.extra?.dual_final_spec;
  if (!initialSpec || !finalSpec) {
    return [];
  }
  const unpagedLimit = Math.max(ctx.limit + ctx.offset, ctx.limit) + 500;
  const base = { db: ctx.db, mode: ctx.mode, code: ctx.code ?? null };
  const initialRows = sortWordRows(await filterMatchSpecRows(initialSpec as MatchSpec, base)).slice(0, unpagedLimit);
  const finalRows = sortWordRows(await filterMatchSpecRows(finalSpec as MatchSpec, base)).slice(0, unpagedLimit);
  const tagged: WordRow[] = [
    ...initialRows.map((row) => ({ ...row, anchor_dimension: 'initial' })),
    ...finalRows.map((row) => ({ ...row, anchor_dimension: 'final' })),
  ];
  return tagged.slice(ctx.offset, ctx.offset + ctx.limit);
}

/** Port of run_position_query_tracked — filter, sort, then page. */
export async function executeMatchSpec(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<WordRow[]> {
  if (!spec || spec.width === 0) {
    return [];
  }
  if (spec.extra?.dual_phoneme) {
    return executeDualPhonemeAnchorSpecs(spec, ctx);
  }
  const filtered = await filterMatchSpecRows(spec, ctx);
  let sorted: WordRow[];
  const literalPositions = spec.extra?.literal_positions;
  if (spec.literal_priority && Array.isArray(literalPositions) && literalPositions.length) {
    const positions = literalPositions as Array<[number, string]>;
    sorted = [...filtered].sort((a, b) => literalPriorityCompare(a, b, positions));
  } else {
    sorted = sortWordRows(filtered);
  }
  return sorted.slice(ctx.offset, ctx.offset + ctx.limit);
}
