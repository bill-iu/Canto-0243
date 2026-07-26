/**
 * Canonical MatchSpec value seam.
 *
 * This module is the migration seam between the existing mutable MatchSpec
 * builders and the strict compiler contract. It deliberately has no database
 * knowledge: callers get one immutable semantic value and execution adapters
 * choose their own physical plan.
 */
import { getEqualsSpan, type EqualsSpan, type MatchSpec, type SlotConstraint } from './spec.ts';

export type CanonicalSlotValue = string | readonly string[];

export interface CanonicalSlotConstraint {
  readonly pos: number;
  readonly kind: SlotConstraint['kind'];
  readonly value: CanonicalSlotValue | null;
}

export interface CanonicalEqualsSpan {
  readonly ref_literal: string;
  readonly ref_jyutping: string | null;
  readonly start_pos: number;
  readonly dimension: 'initial' | 'final';
  readonly phoneme_anchor_only: boolean;
  readonly whole_word: boolean;
}

export interface CanonicalCompoundPolicy {
  readonly kind: NonNullable<MatchSpec['compound_kind']>;
  readonly connective: string | null;
}

export type CandidateScope = 'bounded' | 'complete';
export type RankingPolicy = 'default' | 'literal_priority';

export interface CanonicalMatchSpec {
  readonly width: number;
  readonly slots: readonly CanonicalSlotConstraint[];
  /** Compiler-derived projection for source selection; never an input SSOT. */
  readonly mask: string;
  readonly equals_span: CanonicalEqualsSpan | null;
  readonly compound: CanonicalCompoundPolicy | null;
  readonly ranking: RankingPolicy;
  readonly candidate_scope: CandidateScope;
  readonly code_mode: string | null;
  readonly phoneme_alternatives: {
    readonly initial: CanonicalMatchSpec;
    readonly final: CanonicalMatchSpec;
  } | null;
}

export interface CanonicalMatchSpecDraft {
  width: number;
  slots?: readonly SlotConstraint[];
  mask?: string;
  equals_span?: CanonicalEqualsSpan | null;
  compound_kind?: MatchSpec['compound_kind'];
  connective?: string | null;
  ranking?: RankingPolicy;
  candidate_scope?: CandidateScope;
  code_mode?: string | null;
  phoneme_alternatives?: {
    initial: CanonicalMatchSpec;
    final: CanonicalMatchSpec;
  } | null;
}

function canonicalValue(value: SlotConstraint['value']): CanonicalSlotValue | null {
  if (value == null) return null;
  if (value instanceof Set) return [...value].map(String).sort();
  return String(value);
}

function slotKey(slot: CanonicalSlotConstraint): string {
  return `${slot.pos}\u0000${slot.kind}\u0000${JSON.stringify(slot.value)}`;
}

function freezeEqualsSpan(span: EqualsSpan | null | undefined): CanonicalEqualsSpan | null {
  if (!span) return null;
  return Object.freeze({
    ref_literal: String(span.ref_literal),
    ref_jyutping: span.ref_jyutping == null ? null : String(span.ref_jyutping),
    start_pos: span.start_pos,
    dimension: span.dimension,
    phoneme_anchor_only: Boolean(span.phoneme_anchor_only),
    whole_word: Boolean(span.whole_word),
  });
}

function freezeAlternatives(
  alternatives: CanonicalMatchSpecDraft['phoneme_alternatives'],
): CanonicalMatchSpec['phoneme_alternatives'] {
  if (!alternatives) return null;
  return Object.freeze({ initial: alternatives.initial, final: alternatives.final });
}

/** Finalize one semantic draft at the compiler seam. */
export function finalizeCanonicalMatchSpec(draft: CanonicalMatchSpecDraft): CanonicalMatchSpec {
  if (!Number.isInteger(draft.width) || draft.width <= 0) {
    throw new Error(`MatchSpec width must be a positive integer: ${draft.width}`);
  }

  const slots = (draft.slots ?? []).map((slot) => Object.freeze({
    pos: slot.pos,
    kind: slot.kind,
    value: canonicalValue(slot.value),
  }));
  for (const slot of slots) {
    if (!Number.isInteger(slot.pos) || slot.pos < 0 || slot.pos >= draft.width) {
      throw new Error(`MatchSpec slot position out of range: ${slot.pos}`);
    }
  }
  slots.sort((a, b) => slotKey(a).localeCompare(slotKey(b)));
  for (let i = 1; i < slots.length; i += 1) {
    if (slotKey(slots[i - 1]!) === slotKey(slots[i]!)) {
      throw new Error(`MatchSpec duplicate slot: ${slotKey(slots[i]!)}`);
    }
  }

  const mask = draft.mask == null || draft.mask === '' ? '?'.repeat(draft.width) : draft.mask;
  if ([...mask].length !== draft.width) {
    throw new Error(`MatchSpec mask width mismatch: ${mask.length} != ${draft.width}`);
  }

  const equalsSpan = freezeEqualsSpan(draft.equals_span);
  if (equalsSpan && (equalsSpan.start_pos < 0 || equalsSpan.start_pos >= draft.width)) {
    throw new Error(`MatchSpec equals span position out of range: ${equalsSpan.start_pos}`);
  }

  const compound = draft.compound_kind
    ? Object.freeze({ kind: draft.compound_kind, connective: draft.connective ?? null })
    : null;
  const result: CanonicalMatchSpec = {
    width: draft.width,
    slots: Object.freeze(slots),
    mask,
    equals_span: equalsSpan,
    compound,
    ranking: draft.ranking ?? 'default',
    candidate_scope: draft.candidate_scope ?? 'bounded',
    code_mode: draft.code_mode ?? null,
    phoneme_alternatives: freezeAlternatives(draft.phoneme_alternatives),
  };
  return Object.freeze(result);
}

/**
 * Short-lived migration adapter. New compiler implementations should build a
 * draft directly; this adapter is removed after all callers leave legacy
 * MatchSpec and its open-ended extra bag.
 */
export function canonicalizeLegacyMatchSpec(spec: MatchSpec): CanonicalMatchSpec {
  const raw = spec.extra ?? {};
  const initial = raw.dual_initial_spec as MatchSpec | undefined;
  const final = raw.dual_final_spec as MatchSpec | undefined;
  return finalizeCanonicalMatchSpec({
    width: spec.width,
    slots: spec.slots,
    mask: spec.mask,
    equals_span: getEqualsSpan(spec),
    compound_kind: spec.compound_kind,
    connective: typeof raw.connective === 'string' ? raw.connective : null,
    ranking: spec.literal_priority ? 'literal_priority' : 'default',
    candidate_scope: raw.workbench_full_bucket_scan ? 'complete' : 'bounded',
    code_mode: typeof raw.code_mode === 'string' ? raw.code_mode : null,
    phoneme_alternatives: initial && final
      ? {
        initial: canonicalizeLegacyMatchSpec(initial),
        final: canonicalizeLegacyMatchSpec(final),
      }
      : null,
  });
}

function canonicalJsonValue(value: CanonicalSlotValue | null): unknown {
  return value == null ? null : Array.isArray(value) ? [...value] : value;
}

/** Stable JSON projection for the shared Python／TypeScript golden corpus. */
export function canonicalMatchSpecToJson(spec: CanonicalMatchSpec): Record<string, unknown> {
  return {
    width: spec.width,
    mask: spec.mask,
    slots: spec.slots.map((slot) => ({
      pos: slot.pos,
      kind: slot.kind,
      value: canonicalJsonValue(slot.value),
    })),
    equals_span: spec.equals_span,
    compound: spec.compound,
    ranking: spec.ranking,
    candidate_scope: spec.candidate_scope,
    code_mode: spec.code_mode,
    phoneme_alternatives: spec.phoneme_alternatives
      ? {
        initial: canonicalMatchSpecToJson(spec.phoneme_alternatives.initial),
        final: canonicalMatchSpecToJson(spec.phoneme_alternatives.final),
      }
      : null,
  };
}
