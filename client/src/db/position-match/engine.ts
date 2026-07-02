/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { applyMatchSpec, filterHybridRefCandidates } from './filters.ts';
import { getCandidatesForLength } from './sources.ts';
import { getEqualsSpan, type MatchSpec } from './spec.ts';
import type { WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);

function executeDualPhonemeAnchorSpecs(spec: MatchSpec, ctx: ExecuteMatchSpecContext): WordRow[] {
  const initialSpec = spec.extra?.dual_initial_spec;
  const finalSpec = spec.extra?.dual_final_spec;
  if (!initialSpec || !finalSpec) {
    return [];
  }
  const unpagedLimit = Math.max(ctx.limit + ctx.offset, ctx.limit) + 500;
  const initialRows = executeMatchSpec(initialSpec, { ...ctx, limit: unpagedLimit, offset: 0 });
  const finalRows = executeMatchSpec(finalSpec, { ...ctx, limit: unpagedLimit, offset: 0 });
  const tagged: WordRow[] = [
    ...initialRows.map((row) => ({ ...row, anchor_dimension: 'initial' })),
    ...finalRows.map((row) => ({ ...row, anchor_dimension: 'final' })),
  ];
  return tagged.slice(ctx.offset, ctx.offset + ctx.limit);
}

export type ExecuteMatchSpecContext = {
  db: Database;
  mode: string;
  limit: number;
  offset: number;
  code?: string | null;
};

export function executeMatchSpec(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): WordRow[] {
  if (!spec || spec.width === 0) {
    return [];
  }
  if (spec.extra?.dual_phoneme) {
    return executeDualPhonemeAnchorSpecs(spec, ctx);
  }
  if (getEqualsSpan(spec)) {
    const filtered = applyMatchSpec(spec, [], ctx.db, ctx.mode);
    return filtered.slice(ctx.offset, ctx.offset + ctx.limit);
  }
  if (spec.compound_kind) {
    const filtered = applyMatchSpec(spec, [], ctx.db, ctx.mode);
    return filtered.slice(ctx.offset, ctx.offset + ctx.limit);
  }
  if (spec.hybrid_ref_chars != null && spec.hybrid_ref_pos != null) {
    const [candidates] = getCandidatesForLength(ctx.db, spec.width, {
      code: ctx.code ?? spec.code_prefix ?? null,
      mode: ctx.mode,
    });
    const filtered = filterHybridRefCandidates(candidates, spec, ctx.mode, ctx.db);
    return filtered.slice(ctx.offset, ctx.offset + ctx.limit);
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
  const [candidates] = getCandidatesForLength(ctx.db, spec.width, {
    code,
    mode: ctx.mode,
  });
  const filtered = applyMatchSpec(spec, candidates, ctx.db, ctx.mode);
  return filtered.slice(ctx.offset, ctx.offset + ctx.limit);
}
