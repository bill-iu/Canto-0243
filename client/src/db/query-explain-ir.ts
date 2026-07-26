/**
 * Explain IR build — port of app/services/query_explain_ir.py (ADR-0021)
 */
import type {
  ParsedQuery,
} from './query-engine.ts';
import { QueryKind, normalizeAndParse } from './query-engine.ts';
import {
  buildRequiredCodes,
  codeDigitStringFromSpec,
  hasCodeDigitConstraints,
} from './position-match/filters/f1-slot-code.ts';
import { canonicalMatchSpecToLegacy } from './position-match/canonical.ts';
import { compileParsedQuery } from './position-match/compiler.ts';
import { getEqualsSpan, type EqualsSpan, type MatchSpec } from './position-match/spec.ts';

const WILDCARD_RE = /^[?_%]$/;
const DIGIT_RE = /^\d$/;
const CANTO_RE = /^[一-龥]$/;
const SLOT_PRIORITY: Record<string, number> = {
  wildcard: 0,
  code_digit: 1,
  literal_char: 2,
  final_anchor: 3,
  initial_anchor: 3,
  rhyme_letters: 4,
  initial_letters: 4,
  syllable_letters: 4,
  hybrid_tail_rhyme: 3,
  hybrid_tail_initial: 3,
};

export type ExplainIrVariant =
  | 'whole_word_equals'
  | 'prefix_wildcard_equals'
  | 'code_sandwich_whole_word'
  | 'code_sandwich_scan'
  | 'compound'
  | 'slot_scan'
  | 'fallback';

export interface EqualsIr {
  dimension: 'final' | 'initial';
  ref_literal: string;
  whole_word: boolean;
  start_pos: number;
}

export interface CodePrefixIr {
  digits: string;
  per_digit_full: boolean;
}

export interface CompoundIr {
  kind: string;
  width: number;
  connective?: string;
  code?: string;
  tail_rhyme?: string;
}

export interface PositionConstraintIr {
  pos: number;
  kind: string;
  digit?: string;
  ref?: string;
  char?: string;
  letters?: string;
  symbol?: string;
}

export interface ExplainIr {
  variant: ExplainIrVariant;
  width: number;
  raw_q?: string;
  equals?: EqualsIr;
  code_prefix?: CodePrefixIr;
  compound?: CompoundIr;
  constraints?: PositionConstraintIr[];
}

export function buildExplainIr(spec: MatchSpec, parsed: ParsedQuery): ExplainIr {
  let working = spec;
  if (working.extra?.dual_phoneme) {
    const dual = working.extra.dual_final_spec;
    if (dual && typeof dual === 'object') {
      working = dual as MatchSpec;
    }
  }

  const equals = getEqualsSpan(working);
  if (equals && hasCodeDigitConstraints(working)) {
    return irCodeSandwich(working, equals, parsed);
  }
  if (equals && working.extra?.prefix_wildcard_equals) {
    return irPrefixWildcardEquals(working, equals);
  }
  if (equals?.whole_word) {
    return irWholeWordEquals(working, equals);
  }
  if (working.compound_kind) {
    return irCompound(working);
  }
  return irSlotScan(working, equals);
}

export function explainIrForQuery(q: string, mode: string = 'm1'): ExplainIr | null {
  const text = (q || '').trim();
  if (!text) {
    return null;
  }
  const queryMode = mode === '0243' || mode === '02493' || mode === '394052'
    ? (mode === '02493' ? 'm2' : mode === '394052' ? 'm3' : 'm1')
    : mode;
  const parsed = normalizeAndParse(text, {
    mode: queryMode as import('./query-types.ts').QueryMode,
  });
  if (parsed.kind === QueryKind.UNMATCHED || isShortCircuit(parsed)) {
    return null;
  }
  const spec = canonicalMatchSpecToLegacy(compileParsedQuery(parsed as Parameters<typeof compileParsedQuery>[0]));
  return buildExplainIr(spec, parsed);
}

function isShortCircuit(parsed: ParsedQuery): boolean {
  return (
    parsed.kind === QueryKind.WORD_LOOKUP
    || parsed.kind === QueryKind.DIGIT_CODE
    || parsed.kind === QueryKind.PING_ZE_SERIAL
    || parsed.kind === QueryKind.RELATION_LOOKUP
    || parsed.kind === QueryKind.JYUTPING_FRAGMENT
    || parsed.kind === QueryKind.HETERONYM_CODE
  );
}

function equalsIr(equals: EqualsSpan): EqualsIr {
  const dimension = equals.dimension === 'final' || equals.dimension === 'rhyme'
    ? 'final'
    : 'initial';
  return {
    dimension,
    ref_literal: equals.ref_literal,
    whole_word: Boolean(equals.whole_word),
    start_pos: equals.start_pos,
  };
}

function codePrefixIr(spec: MatchSpec): CodePrefixIr | null {
  const code = codeDigitStringFromSpec(spec);
  if (!code) {
    return null;
  }
  const required = buildRequiredCodes(spec);
  const perDigitFull = required.every((d) => d != null) && required.length === spec.width;
  return { digits: code, per_digit_full: perDigitFull };
}

function constraintsToIr(constraints: Map<number, [string, string]>): PositionConstraintIr[] {
  return [...constraints.entries()]
    .sort(([a], [b]) => a - b)
    .map(([pos, [kind, value]]) => {
      const entry: PositionConstraintIr = { pos, kind };
      if (kind === 'code_digit') {
        entry.digit = value;
      } else if (kind === 'literal_char') {
        entry.char = value;
      } else if (kind === 'wildcard') {
        entry.symbol = value;
      } else if (kind === 'final_anchor' || kind === 'initial_anchor') {
        entry.ref = value;
      } else if (kind === 'rhyme_letters' || kind === 'initial_letters' || kind === 'syllable_letters') {
        entry.letters = value;
      } else if (
        kind === 'hybrid_tail_rhyme'
        || kind === 'hybrid_tail_initial'
        || kind === 'hybrid_code_literal'
      ) {
        const [digit, ref] = value.split('|', 2);
        entry.digit = digit;
        entry.ref = ref;
      } else {
        entry.ref = value;
      }
      return entry;
    });
}

function irWholeWordEquals(spec: MatchSpec, equals: EqualsSpan): ExplainIr {
  const ir: ExplainIr = {
    variant: 'whole_word_equals',
    width: spec.width,
    equals: equalsIr(equals),
  };
  const codePrefix = codePrefixIr(spec);
  if (codePrefix) {
    ir.code_prefix = codePrefix;
  }
  return ir;
}

function irPrefixWildcardEquals(spec: MatchSpec, equals: EqualsSpan): ExplainIr {
  return {
    variant: 'prefix_wildcard_equals',
    width: spec.width,
    equals: equalsIr(equals),
  };
}

function irCodeSandwich(spec: MatchSpec, equals: EqualsSpan, parsed: ParsedQuery): ExplainIr {
  const raw = parsed.raw_q || '';
  if (equals.whole_word) {
    const ir: ExplainIr = {
      variant: 'code_sandwich_whole_word',
      width: spec.width,
      raw_q: raw,
      equals: equalsIr(equals),
    };
    const codePrefix = codePrefixIr(spec);
    if (codePrefix) {
      ir.code_prefix = codePrefix;
    }
    return ir;
  }
  const constraints = effectiveConstraints(spec, equals);
  return {
    variant: 'code_sandwich_scan',
    width: spec.width,
    raw_q: raw,
    constraints: constraintsToIr(constraints),
  };
}

function irCompound(spec: MatchSpec): ExplainIr {
  const compound: CompoundIr = {
    kind: spec.compound_kind!,
    width: spec.width,
  };
  if (spec.compound_kind === 'doubled_syllable') {
    const rhyme = (spec.slots ?? []).find(
      (s) => s.kind === 'final_anchor' && typeof s.value === 'string',
    )?.value as string | undefined;
    const code = codeDigitStringFromSpec(spec);
    if (code) {
      compound.code = code;
    }
    if (rhyme) {
      compound.tail_rhyme = rhyme;
    }
  } else {
    const connective = spec.extra?.connective;
    if (typeof connective === 'string' && connective) {
      compound.connective = connective;
    }
  }
  return { variant: 'compound', width: spec.width, compound };
}

function irSlotScan(spec: MatchSpec, equals: EqualsSpan | null): ExplainIr {
  const constraints = effectiveConstraints(spec, equals);
  return {
    variant: 'slot_scan',
    width: spec.width,
    constraints: constraintsToIr(constraints),
  };
}

function effectiveConstraints(
  spec: MatchSpec,
  equals: EqualsSpan | null,
): Map<number, [string, string]> {
  const result = new Map<number, [string, string]>();

  for (const [i, digit] of buildRequiredCodes(spec).entries()) {
    if (digit != null) {
      result.set(i, ['code_digit', digit]);
    }
  }

  if (spec.mask) {
    for (let i = 0; i < spec.mask.length && i < spec.width; i++) {
      const ch = spec.mask[i]!;
      if (WILDCARD_RE.test(ch)) {
        if (!result.has(i)) {
          result.set(i, ['wildcard', ch]);
        }
      } else if (DIGIT_RE.test(ch)) {
        if (!result.has(i)) {
          result.set(i, ['code_digit', ch]);
        }
      } else if (CANTO_RE.test(ch)) {
        if (!result.has(i)) {
          result.set(i, ['literal_char', ch]);
        }
      }
    }
  }

  for (const slot of spec.slots ?? []) {
    let value: string;
    if (slot.value instanceof Set) {
      value = slot.value.values().next().value ?? '';
    } else {
      value = slot.value != null ? String(slot.value) : '';
    }
    const existing = result.get(slot.pos);
    if (slot.kind === 'final_anchor' && existing?.[0] === 'code_digit') {
      result.set(slot.pos, ['hybrid_tail_rhyme', `${existing[1]}|${value}`]);
      continue;
    }
    if (slot.kind === 'initial_anchor' && existing?.[0] === 'code_digit') {
      result.set(slot.pos, ['hybrid_tail_initial', `${existing[1]}|${value}`]);
      continue;
    }
    if (slot.kind === 'literal_char' && existing?.[0] === 'code_digit') {
      result.set(slot.pos, ['hybrid_code_literal', `${existing[1]}|${value}`]);
      continue;
    }
    if (
      existing
      && (SLOT_PRIORITY[existing[0]] ?? 0) >= (SLOT_PRIORITY[slot.kind] ?? 0)
    ) {
      continue;
    }
    result.set(slot.pos, [slot.kind, value]);
  }

  if (equals && !equals.whole_word) {
    const required = buildRequiredCodes(spec);
    const dimKind = equals.dimension === 'final' || equals.dimension === 'rhyme'
      ? 'final_anchor'
      : 'initial_anchor';
    for (let i = 0; i < equals.ref_literal.length; i++) {
      const pos = equals.start_pos + i;
      if (pos < 0 || pos >= spec.width) {
        continue;
      }
      const digit = pos < required.length ? required[pos] ?? undefined : undefined;
      if (
        digit != null
        && (equals.dimension === 'final' || equals.dimension === 'rhyme')
        && !equals.phoneme_anchor_only
      ) {
        result.set(pos, ['hybrid_tail_rhyme', `${digit}|${equals.ref_literal[i]}`]);
      } else if (equals.phoneme_anchor_only && digit != null) {
        const kind =
          equals.dimension === 'final' || equals.dimension === 'rhyme'
            ? 'hybrid_tail_rhyme'
            : 'hybrid_tail_initial';
        result.set(pos, [kind, `${digit}|${equals.ref_literal[i]}`]);
      } else {
        result.set(pos, [dimKind, equals.ref_literal[i]!]);
      }
    }
  }

  return result;
}
