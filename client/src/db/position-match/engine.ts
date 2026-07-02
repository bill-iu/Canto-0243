/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { applyMatchSpec, filterHybridRefCandidates } from './filters.ts';
import { getCandidatesForLength } from './sources.ts';
import { getEqualsSpan, type MatchSpec } from './spec.ts';
import type { WordRow } from './word-row.ts';

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
    return [];
  }
  if (getEqualsSpan(spec)) {
    return [];
  }
  if (spec.hybrid_ref_chars != null && spec.hybrid_ref_pos != null) {
    const [candidates] = getCandidatesForLength(ctx.db, spec.width, {
      code: ctx.code ?? spec.code_prefix ?? null,
      mode: ctx.mode,
    });
    const filtered = filterHybridRefCandidates(candidates, spec, ctx.mode, ctx.db);
    return filtered.slice(ctx.offset, ctx.offset + ctx.limit);
  }

  const hasPhonemeAnchors = (spec.slots ?? []).some(
    (s) => s.kind === 'final_anchor' || s.kind === 'initial_anchor',
  );
  if (!hasPhonemeAnchors && !spec.mask) {
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
