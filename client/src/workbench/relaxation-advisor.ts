import type { RelaxationKind, ReplacementPlanV1 } from './contracts.ts';

export interface RelaxationVariant {
  id: string;
  kind: RelaxationKind;
  positions?: number[];
  from?: string;
  to?: string;
  plan: ReplacementPlanV1;
}

export function relaxationVariants(plan: ReplacementPlanV1): RelaxationVariant[] {
  const variants: RelaxationVariant[] = [];
  if (plan.semanticIntent === 'direct_only') {
    variants.push({
      id: 'semantic:direct_only:ranked',
      kind: 'semantic_ranked',
      from: 'direct_only',
      to: 'ranked',
      plan: { ...plan, semanticIntent: 'ranked' },
    });
  }
  const removals: Array<[string, RelaxationKind]> = [
    ['final_anchor', 'remove_final'],
    ['initial_anchor', 'remove_initial'],
    ['code_digit', 'remove_code'],
  ];
  for (const [slotKind, kind] of removals) {
    for (let index = 0; index < plan.slots.length; index += 1) {
      const slot = plan.slots[index]!;
      if (slot.kind !== slotKind) continue;
      variants.push({
        id: `${slotKind}:${slot.pos}:remove`,
        kind,
        positions: [slot.pos],
        from: slotKind,
        plan: { ...plan, slots: plan.slots.filter((_item, itemIndex) => itemIndex !== index) },
      });
    }
  }
  const nextMode = plan.mode === 'm3' ? 'm2' : plan.mode === 'm2' ? 'm1' : null;
  if (nextMode) {
    variants.push({
      id: `mode:${plan.mode}:${nextMode}`,
      kind: 'loosen_mode',
      from: plan.mode,
      to: nextMode,
      plan: { ...plan, mode: nextMode },
    });
  }
  return variants;
}

/** Ordered relaxation ids for L3 parity. */
export function relaxationIds(plan: ReplacementPlanV1): string[] {
  return relaxationVariants(plan).map((variant) => variant.id);
}
