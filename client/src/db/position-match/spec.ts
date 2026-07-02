/**
 * Position match core types — port of app/services/position_match/spec.py (MF-1)
 */

export type ConstraintKind =
  | 'code_digit'
  | 'literal_char'
  | 'final_anchor'
  | 'initial_anchor'
  | 'rhyme_letters'
  | 'syllable_letters'
  | 'initial_letters'
  | 'wildcard';

export type SlotConstraintValue = string | ReadonlySet<string>;

export interface SlotConstraint {
  pos: number;
  kind: ConstraintKind;
  value?: SlotConstraintValue | null;
}

/** Python EqualsSpan.dimension; TS executors also accept rhyme/phone aliases */
export type EqualsSpanDimension = 'initial' | 'final';

export type EqualsDimension = EqualsSpanDimension | 'rhyme' | 'phone';

export interface EqualsSpan {
  ref_literal: string;
  start_pos: number;
  dimension: EqualsDimension;
  phoneme_anchor_only: boolean;
  whole_word: boolean;
}

export type CompoundKind = 'syn' | 'ant' | 'doubled_syllable';

export interface MatchSpec {
  width: number;
  slots?: SlotConstraint[];
  code_prefix?: string | null;
  literal_priority?: boolean;
  hybrid_ref_chars?: string | null;
  hybrid_ref_pos?: number | null;
  mask?: string;
  compound_kind?: CompoundKind | null;
  extra?: Record<string, unknown>;
}

export interface MaskFamilySearchResult {
  items: unknown[];
  cache_path?: string | null;
}

export interface CandidateSource {
  getCandidates(
    length: number,
    options?: { code?: string | null; mode?: string },
  ): [unknown[], boolean];
}

const EQUALS_SPAN_KEY = 'equals_span';

export function getEqualsSpan(spec: MatchSpec): EqualsSpan | null {
  const raw = spec.extra?.[EQUALS_SPAN_KEY];
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  return raw as EqualsSpan;
}

export function attachEqualsSpan(spec: MatchSpec, span: EqualsSpan): void {
  if (!spec.extra) {
    spec.extra = {};
  }
  spec.extra[EQUALS_SPAN_KEY] = span;
}

export function createMatchSpec(width: number, fields: Omit<MatchSpec, 'width'> = {}): MatchSpec {
  return { width, slots: [], mask: '', extra: {}, ...fields };
}

/** ponytail: runnable self-check — `npx tsx client/scripts/position-match-spec-self-check.ts` */
export function positionMatchSpecSelfCheck(): void {
  const spec = createMatchSpec(2, { code_prefix: '23', mask: '?就' });
  if (spec.width !== 2 || spec.code_prefix !== '23') {
    throw new Error('positionMatchSpecSelfCheck: createMatchSpec');
  }

  const span: EqualsSpan = {
    ref_literal: '香港',
    start_pos: 0,
    dimension: 'final',
    phoneme_anchor_only: false,
    whole_word: true,
  };
  attachEqualsSpan(spec, span);
  const roundtrip = getEqualsSpan(spec);
  if (!roundtrip || roundtrip.ref_literal !== '香港' || !roundtrip.whole_word) {
    throw new Error('positionMatchSpecSelfCheck: equals_span roundtrip');
  }

  spec.slots!.push({ pos: 1, kind: 'literal_char', value: '就' });
  if (spec.slots!.length !== 1 || spec.slots![0]!.kind !== 'literal_char') {
    throw new Error('positionMatchSpecSelfCheck: slots');
  }
}
