/**
 * 查詢語意解釋 — port of app/services/query_explain.py (ADR-0021)
 */
import type {
  DigitCodeQuery,
  HeteronymCodeQuery,
  JyutpingAnchorQuery,
  JyutpingFragmentQuery,
  ParsedQuery,
  RelationLookupQuery,
  UnmatchedQuery,
  WordLookupQuery,
} from './query-engine.ts';
import { QueryKind, normalizeAndParse } from './query-engine.ts';
import { slotLabel } from './ping-zak.ts';
import {
  buildRequiredCodes,
  codeDigitStringFromSpec,
  hasCodeDigitConstraints,
} from './position-match/filters/f1-slot-code.ts';
import { buildMatchSpecForParsed } from './position-match/match-spec-registry.ts';
import { getEqualsSpan, type EqualsSpan, type MatchSpec } from './position-match/spec.ts';

const WILDCARD_RE = /^[?_%]$/;
const DIGIT_RE = /^\d$/;
const CANTO_RE = /^[一-龥]$/;
const CN_WIDTH = ['', '一', '兩', '三', '四', '五', '六', '七', '八', '九', '十'];
const RHYME_LABELS = ['', '單押', '雙押', '三押', '四押'];
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

export interface QueryExplainResult {
  summary: string | null;
  warning: string | null;
  kind: string | null;
}

export function explainQuery(q: string, mode: string = 'm1'): QueryExplainResult {
  const text = (q || '').trim();
  if (!text) {
    return { summary: null, warning: null, kind: null };
  }
  const queryMode = mode === '0243' || mode === '02493' || mode === '394052'
    ? (mode === '02493' ? 'm2' : mode === '394052' ? 'm3' : 'm1')
    : mode;
  const parsed = normalizeAndParse(text, {
    mode: queryMode as import('./query-types.ts').QueryMode,
  });
  const warning = warningFor(parsed);
  if (parsed.kind === QueryKind.UNMATCHED) {
    const unmatched = parsed as UnmatchedQuery;
    return {
      summary: null,
      warning: unmatched.hint || warning,
      kind: parsed.kind,
    };
  }
  return {
    summary: summaryFor(parsed),
    warning,
    kind: parsed.kind,
  };
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

export function renderExplainIr(ir: ExplainIr): string {
  switch (ir.variant) {
    case 'whole_word_equals':
      return renderWholeWordEquals(ir);
    case 'prefix_wildcard_equals':
      return renderPrefixWildcardEquals(ir);
    case 'code_sandwich_whole_word':
      return renderCodeSandwichWholeWord(ir);
    case 'code_sandwich_scan':
      return renderCodeSandwichScan(ir);
    case 'compound':
      return renderCompound(ir);
    case 'slot_scan':
      return renderSlotScan(ir);
    default:
      return widthLabel(ir.width);
  }
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
  const spec = buildMatchSpecForParsed(parsed);
  if (!spec) {
    return null;
  }
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

function wordPos(n: number): string {
  return `第 ${n + 1} 個字`;
}

function widthLabel(width: number): string {
  const cn = width < CN_WIDTH.length ? CN_WIDTH[width] : String(width);
  return `${cn}個字`;
}

function rhymeLabel(n: number): string {
  return n < RHYME_LABELS.length ? RHYME_LABELS[n]! : `${n}押`;
}

function rhymeOrInitial(dimension: string): string {
  return dimension === 'final' || dimension === 'rhyme' ? '同韻' : '同聲';
}

function posListLabel(positions: number[]): string {
  if (positions.length === 1) {
    return wordPos(positions[0]!);
  }
  const nums = positions.map((p) => `第 ${p + 1}`).join('、');
  return `${nums} 個字`;
}

function summaryFor(parsed: ParsedQuery): string | null {
  if (parsed.kind === QueryKind.WORD_LOOKUP) {
    return `查詢詞條「${(parsed as WordLookupQuery).raw_q}」`;
  }
  if (parsed.kind === QueryKind.DIGIT_CODE) {
    return `查同${(parsed as DigitCodeQuery).raw_q}同音嘅字`;
  }
  if (parsed.kind === QueryKind.PING_ZE_SERIAL) {
    const pz = parsed as import('./query-types.ts').PingZeSerialQuery;
    const parts = [...pz.raw_q].map((ch) => slotLabel(ch));
    return `查${parts.join('、')}嘅${widthLabel(pz.raw_q.length)}詞`;
  }
  if (parsed.kind === QueryKind.RELATION_LOOKUP) {
    const rel = parsed as RelationLookupQuery;
    const label = rel.relation_kind === 'syn' ? '近義詞' : '反義詞';
    const prefix = rel.code_prefix ? `碼 ${rel.code_prefix} ` : '';
    return `查「${rel.word}」嘅${prefix}${label}`;
  }
  if (parsed.kind === QueryKind.JYUTPING_FRAGMENT) {
    const raw = (parsed as JyutpingFragmentQuery).raw_q;
    const tone = /[1-6]/.test(raw) ? '（有聲調）' : '（不需聲調）';
    return `粵拼查詢「${raw}」${tone}`;
  }
  if (parsed.kind === QueryKind.HETERONYM_CODE) {
    const h = parsed as HeteronymCodeQuery;
    return (
      `查同字面異讀（${h.left_template}/${h.right_template}）：` +
      '搵至少兩個唔同讀音，分別符合左右碼位模板'
    );
  }
  if (parsed.kind === QueryKind.UNMATCHED) {
    return null;
  }

  const spec = buildMatchSpecForParsed(parsed);
  if (!spec) {
    const raw = parsed.raw_q;
    return raw ? `查詢「${raw}」` : '查詢';
  }
  return renderExplainIr(buildExplainIr(spec, parsed));
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

function renderCodePrefixPhrase(codePrefix: CodePrefixIr): string {
  if (codePrefix.per_digit_full) {
    const parts = [...codePrefix.digits].map((digit, i) => `${wordPos(i)}同 ${digit} 同音`);
    return parts.join('，');
  }
  return `前 ${codePrefix.digits.length} 個字為碼 ${codePrefix.digits}`;
}

function renderWholeWordEquals(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const line = `整詞同「${equals.ref_literal}」${dim}（${label}）`;
  if (ir.code_prefix) {
    return `${line}；${renderCodePrefixPhrase(ir.code_prefix)}`;
  }
  return line;
}

function renderPrefixWildcardEquals(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const positions = Array.from(
    { length: ir.width - equals.start_pos },
    (_, i) => equals.start_pos + i,
  );
  const posLabel = posListLabel(positions);
  return `首個字任意；${posLabel}同「${equals.ref_literal}」${dim}（${label}）`;
}

function renderCodeSandwichWholeWord(ir: ExplainIr): string {
  const equals = ir.equals!;
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const rhymeLine = `同「${equals.ref_literal}」${dim}（${label}）`;
  const body = ir.code_prefix
    ? `${rhymeLine}；${renderCodePrefixPhrase(ir.code_prefix)}`
    : rhymeLine;
  return `數字夾字「${ir.raw_q}」：${body}`;
}

function renderConstraintPhrase(c: PositionConstraintIr): string {
  const label = wordPos(c.pos);
  if (c.kind === 'code_digit') {
    return `${label}同 ${c.digit} 同音`;
  }
  if (c.kind === 'literal_char') {
    return `${label}為「${c.char}」`;
  }
  if (c.kind === 'wildcard') {
    return `${label}任意字`;
  }
  if (c.kind === 'hybrid_tail_rhyme') {
    return `${label}同 ${c.digit} 同音且同「${c.ref}」同韻`;
  }
  if (c.kind === 'hybrid_tail_initial') {
    return `${label}同 ${c.digit} 同音且同「${c.ref}」同聲`;
  }
  if (c.kind === 'hybrid_code_literal') {
    return `${label}同 ${c.digit} 同音且限定為${c.ref}`;
  }
  if (c.kind === 'final_anchor') {
    return `${label}同「${c.ref}」同韻`;
  }
  if (c.kind === 'initial_anchor') {
    return `${label}同「${c.ref}」同聲`;
  }
  if (c.kind === 'rhyme_letters') {
    return `${label}同韻母 ${c.letters}`;
  }
  if (c.kind === 'initial_letters') {
    return `${label}同聲母 ${c.letters}`;
  }
  if (c.kind === 'syllable_letters') {
    return `${label}粵拼音節 ${c.letters}`;
  }
  return `${label}為「${c.ref ?? ''}」`;
}

function renderConstraints(constraints: PositionConstraintIr[]): string {
  return constraints.map((c) => renderConstraintPhrase(c)).join('，');
}

function renderCodeSandwichScan(ir: ExplainIr): string {
  const constraints = ir.constraints ?? [];
  if (constraints.length) {
    return `數字夾字「${ir.raw_q}」：${renderConstraints(constraints)}`;
  }
  return `數字夾字「${ir.raw_q}」`;
}

function renderCompound(ir: ExplainIr): string {
  const compound = ir.compound!;
  if (compound.kind === 'doubled_syllable') {
    const n = compound.width;
    const base = `查${n}字雙聲疊韻字（各字音節相同，聲調不限）`;
    if (compound.code && compound.tail_rhyme) {
      return `查${n}字雙聲疊韻字（碼 ${compound.code}，尾字同「${compound.tail_rhyme}」同韻）`;
    }
    if (compound.code) {
      return `查${n}字雙聲疊韻字（碼 ${compound.code}）`;
    }
    if (compound.tail_rhyme) {
      return `查${n}字雙聲疊韻字（尾字同「${compound.tail_rhyme}」同韻）`;
    }
    return base;
  }
  const label = compound.kind === 'syn' ? '近義' : '反義';
  if (compound.connective) {
    return `查詢含「${compound.connective}」嘅${label}複合詞`;
  }
  return `查詢${label}複合詞`;
}

function renderSlotScan(ir: ExplainIr): string {
  const constraints = ir.constraints ?? [];
  if (!constraints.length) {
    return widthLabel(ir.width);
  }
  return `${widthLabel(ir.width)}：${renderConstraints(constraints)}`;
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

function warningFor(parsed: ParsedQuery): string | null {
  if (parsed.kind !== QueryKind.JYUTPING_ANCHOR) {
    return null;
  }
  const anchor = parsed as JyutpingAnchorQuery;
  if (!anchor.hybrid_rhyme || anchor.anchor_kind !== 'rhyme_letters') {
    return null;
  }
  const value = anchor.anchor_value;
  const prefix = anchor.code_prefix || '';
  if (anchor.width === 2 && !anchor.raw_q.includes('+')) {
    return `易混：三個字請改「${prefix}+${value}」`;
  }
  if (anchor.width >= 3 && anchor.raw_q.includes('+')) {
    return `易混：兩個字請改「${prefix}${value}」`;
  }
  return null;
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p2-explain-self-check.ts` */
export function queryExplainLogicSelfCheck(): void {
  const equals = explainQuery('香港=');
  if (!equals.summary?.includes('雙押')) {
    throw new Error(`queryExplainLogicSelfCheck: 香港= ${equals.summary}`);
  }
  const warn = explainQuery('23ng');
  if (!warn.warning?.includes('易混')) {
    throw new Error(`queryExplainLogicSelfCheck: 23ng warning ${warn.warning}`);
  }
  const noTone = explainQuery('nei hou');
  if (!noTone.summary?.includes('不需聲調')) {
    throw new Error(`queryExplainLogicSelfCheck: nei hou ${noTone.summary}`);
  }
  const withTone = explainQuery('ming4 baak6');
  if (!withTone.summary?.includes('有聲調')) {
    throw new Error(`queryExplainLogicSelfCheck: ming4 baak6 ${withTone.summary}`);
  }
  const pz = explainQuery('PZ', 'pz');
  if (!pz.summary?.includes('平')) {
    throw new Error(`queryExplainLogicSelfCheck: PZ pz ${pz.summary}`);
  }
}
