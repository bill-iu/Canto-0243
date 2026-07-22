import {
  buildCodeDigitSlots,
  planHasQueryableSlots,
} from '../code-constraint.ts';
import {
  WORKBENCH_CANDIDATE_PAGE_SIZE,
  type ReplacementPlanV1,
  type WorkbenchSlotConstraintV1,
} from '../contracts.ts';
import { isHanSurface } from '../wildcard-slot.ts';
import type { SessionPaging, WorkbenchSession } from './types.ts';

/** Plan 核心（無 paging）— 用時計算，唔存 session。 */
export function derivePlanBase(
  session: WorkbenchSession,
): Omit<ReplacementPlanV1, 'limit' | 'offset'> | null {
  const draft = session.draft;
  if (!draft?.selection) return null;
  const { start, width } = draft.selection;
  const span = draft.selection;
  const { mode, semanticIntent, codeConstraint, explicitCode } = session.constraints;

  const base: WorkbenchSlotConstraintV1[] = draft.constraints
    .filter((item) => item.kind !== 'code_digit' && item.pos >= start && item.pos < start + width)
    .map((item) => ({ ...item, pos: item.pos - start }));
  const codes = buildCodeDigitSlots(codeConstraint, draft.slots, span, explicitCode);
  const slots = [...base, ...codes];
  const semanticSeed = draft.slots
    .slice(start, start + width)
    .map((slot) => slot.surface)
    .filter((surface) => isHanSurface(surface))
    .join('');
  const intent = semanticSeed ? semanticIntent : 'off';
  if (!planHasQueryableSlots(width, slots, semanticSeed, intent)) return null;

  return {
    version: 1 as const,
    selectionVersion: session.version,
    width,
    mode,
    slots,
    semanticIntent: intent,
    semanticSeed: semanticSeed || undefined,
  };
}

/** 完整 ReplacementPlanV1；paging 係參數，唔係 session 真相。 */
export function derivePlan(
  session: WorkbenchSession,
  paging: SessionPaging = { offset: 0, limit: WORKBENCH_CANDIDATE_PAGE_SIZE },
): ReplacementPlanV1 | null {
  const base = derivePlanBase(session);
  if (!base) return null;
  return {
    ...base,
    limit: paging.limit,
    offset: paging.offset,
  };
}
