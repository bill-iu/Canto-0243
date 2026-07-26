import { attachEqualsSpan, type MatchSpec, type SlotConstraint } from '../db/position-match/spec.ts';
import {
  canonicalMatchSpecToLegacy,
  finalizeCanonicalMatchSpec,
  type CanonicalMatchSpec,
} from '../db/position-match/canonical.ts';
import type { ReplacementPlanV1 } from './contracts.ts';

/** plan → MatchSpec（L1）；權威名 buildMatchSpec；舊 buildPwaMatchSpec re-export。 */
export function buildMatchSpec(plan: ReplacementPlanV1): MatchSpec {
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

/** @deprecated use buildMatchSpec */
export const buildPwaMatchSpec = buildMatchSpec;

/** ReplacementPlan domain input → canonical immutable MatchSpec. */
export function compileReplacementPlan(plan: ReplacementPlanV1): CanonicalMatchSpec {
  const mask = Array.from({ length: plan.width }, () => '?');
  const slots: SlotConstraint[] = plan.slots.map((item) => {
    const value = item.kind === 'code_digit' ? item.digit
      : item.kind === 'literal_char' ? item.literal
        : item.kind === 'tone_class' ? item.toneClass
          : item.ref;
    if (item.kind === 'literal_char' && item.literal) mask[item.pos] = item.literal;
    return { pos: item.pos, kind: item.kind, value };
  });
  let equalsSpan: CanonicalMatchSpec['equals_span'] = null;
  for (const [kind, dimension] of [['final_anchor', 'final'], ['initial_anchor', 'initial']] as const) {
    const anchorItems = plan.slots.filter((slot) => slot.kind === kind).sort((a, b) => a.pos - b.pos);
    const anchors = slots.filter((slot) => slot.kind === kind).sort((a, b) => a.pos - b.pos);
    const positions = anchors.map((slot) => slot.pos);
    const contiguous = positions.length >= 2
      && positions.every((pos, index) => index === 0 || pos === positions[index - 1]! + 1);
    if (!contiguous || anchorItems.some((slot) => !slot.refJyutping)) continue;
    equalsSpan = {
      ref_literal: anchors.map((slot) => String(slot.value ?? '')).join(''),
      ref_jyutping: anchorItems.map((slot) => slot.refJyutping ?? '').join(' ') || null,
      start_pos: positions[0]!,
      dimension,
      phoneme_anchor_only: true,
      whole_word: positions[0] === 0 && positions.length === plan.width,
    };
    for (let i = slots.length - 1; i >= 0; i -= 1) {
      if (slots[i]!.kind === kind) slots.splice(i, 1);
    }
    break;
  }
  return finalizeCanonicalMatchSpec({
    width: plan.width,
    slots,
    mask: mask.join(''),
    equals_span: equalsSpan,
    candidate_scope: 'complete',
  });
}

/** Canonical JSON for L1 parity (stable key order for equals_span). */
export function matchSpecToCanonical(spec: MatchSpec): Record<string, unknown> {
  const slots = (spec.slots ?? []).map((slot) => ({
    pos: slot.pos,
    kind: slot.kind,
    value: slot.value instanceof Set ? [...slot.value].sort() : (slot.value ?? null),
  }));
  const extra: Record<string, unknown> = {};
  const raw = spec.extra ?? {};
  if (raw.equals_span && typeof raw.equals_span === 'object') {
    const span = raw.equals_span as Record<string, unknown>;
    extra.equals_span = {
      ref_literal: span.ref_literal ?? '',
      ref_jyutping: span.ref_jyutping ?? null,
      start_pos: span.start_pos ?? 0,
      dimension: span.dimension ?? 'final',
      phoneme_anchor_only: Boolean(span.phoneme_anchor_only),
      whole_word: Boolean(span.whole_word),
    };
  }
  if (raw.prefix_wildcard_equals) {
    extra.prefix_wildcard_equals = true;
  }
  return {
    width: spec.width,
    mask: spec.mask ?? '',
    slots,
    extra,
  };
}
