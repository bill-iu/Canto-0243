/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { sortWordRows, literalPriorityCompare } from '../ranking.ts';
import { throwIfSearchCancelled, type ShouldCancel } from '../search-cancel.ts';
import { applyMatchSpec } from './filters.ts';
import { getCandidatesForLength, getLengthMaskCandidates } from './sources.ts';
import { getEqualsSpan, type MatchSpec } from './spec.ts';
import type { WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);

function shouldUseMaskCandidates(spec: MatchSpec): boolean {
  // ponytail: only when mask has fixed CJK literals (not pure ?? / digit masks)
  if (!spec.mask || spec.compound_kind || getEqualsSpan(spec)) {
    return false;
  }
  // Pure ? or code-digit masks have no char GLOB value — use length+code path instead
  // (fixes 3$漢4 etc. loading all width-N rows via GLOB ??)
  if (!/[^\d?]/.test(spec.mask)) {
    return false;
  }
  return true;
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
  shouldCancel?: ShouldCancel;
};

/** Filter all matching rows — port of PositionMatchEngine.match (no sort/page). */
export async function filterMatchSpecRows(
  spec: MatchSpec,
  ctx: Pick<ExecuteMatchSpecContext, 'db' | 'mode' | 'code' | 'shouldCancel'>,
): Promise<WordRow[]> {
  if (!spec || spec.width === 0) {
    return [];
  }
  throwIfSearchCancelled(ctx.shouldCancel);
  if (getEqualsSpan(spec) || spec.compound_kind) {
    return applyMatchSpec(spec, [], ctx.db, ctx.mode, ctx.shouldCancel);
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
      ? await getLengthMaskCandidates(ctx.db, spec.width, spec.mask, {
          code,
          mode: ctx.mode,
        })
      : await getCandidatesForLength(ctx.db, spec.width, {
          code,
          mode: ctx.mode,
          // Only force unlimited when no code can narrow the set
          unlimited: specNeedsFullLengthBucket(spec) && !code,
        });
  throwIfSearchCancelled(ctx.shouldCancel);
  return applyMatchSpec(spec, candidates, ctx.db, ctx.mode, ctx.shouldCancel);
}

async function executeDualPhonemeAnchorSpecs(spec: MatchSpec, ctx: ExecuteMatchSpecContext): Promise<WordRow[]> {
  const initialSpec = spec.extra?.dual_initial_spec;
  const finalSpec = spec.extra?.dual_final_spec;
  if (!initialSpec || !finalSpec) {
    return [];
  }
  const unpagedLimit = Math.max(ctx.limit + ctx.offset, ctx.limit) + 500;
  const base = {
    db: ctx.db,
    mode: ctx.mode,
    code: ctx.code ?? null,
    shouldCancel: ctx.shouldCancel,
  };
  const initialRows = sortWordRows(await filterMatchSpecRows(initialSpec as MatchSpec, base)).slice(
    0,
    unpagedLimit,
  );
  throwIfSearchCancelled(ctx.shouldCancel);
  const finalRows = sortWordRows(await filterMatchSpecRows(finalSpec as MatchSpec, base)).slice(
    0,
    unpagedLimit,
  );
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
  throwIfSearchCancelled(ctx.shouldCancel);
  let sorted: WordRow[];
  const literalPositions = spec.extra?.literal_positions;
  if (spec.literal_priority && Array.isArray(literalPositions) && literalPositions.length) {
    const positions = literalPositions as Array<[number, string]>;
    sorted = [...filtered].sort((a, b) => literalPriorityCompare(a, b, positions));
  } else {
    sorted = sortWordRows(filtered);
  }
  // E3: only return the requested window
  return sorted.slice(ctx.offset, ctx.offset + ctx.limit);
}
