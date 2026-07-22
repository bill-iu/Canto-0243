import type { ReplacementPlanV1 } from './contracts.ts';

/** Canonical candidate identity; draft version and paging are not query inputs. */
export function candidateSnapshotIdentity(plan: ReplacementPlanV1): string {
  const slots = plan.slots
    .map((slot) => Object.fromEntries(
      Object.entries(slot).filter(([, value]) => value != null),
    ))
    .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
  return JSON.stringify({
    version: plan.version,
    width: plan.width,
    mode: plan.mode,
    slots,
    semanticIntent: plan.semanticIntent,
    semanticSeed: plan.semanticSeed ?? null,
  });
}
