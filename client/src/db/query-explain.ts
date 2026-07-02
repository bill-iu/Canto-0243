/**
 * 查詢語意解釋 — port of app/services/query_explain.py (ADR-0021)
 */
import type {
  CompoundDoubledSyllableQuery,
  DigitCodeQuery,
  HeteronymCodeQuery,
  HybridTailEqualsAliasQuery,
  JyutpingAnchorQuery,
  JyutpingFragmentQuery,
  ParsedQuery,
  RelationLookupQuery,
  UnmatchedQuery,
  WordLookupQuery,
} from './query-engine.ts';
import { QueryKind, normalizeAndParse } from './query-engine.ts';
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

export interface QueryExplainResult {
  summary: string | null;
  warning: string | null;
  kind: string | null;
}

export function explainQuery(q: string, _mode: string = 'm1'): QueryExplainResult {
  const text = (q || '').trim();
  if (!text) {
    return { summary: null, warning: null, kind: null };
  }
  const parsed = normalizeAndParse(text);
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
  if (parsed.kind === QueryKind.RELATION_LOOKUP) {
    const rel = parsed as RelationLookupQuery;
    const label = rel.relation_kind === 'syn' ? '近義詞' : '反義詞';
    const prefix = rel.code_prefix ? `碼 ${rel.code_prefix} ` : '';
    return `查「${rel.word}」嘅${prefix}${label}`;
  }
  if (parsed.kind === QueryKind.JYUTPING_FRAGMENT) {
    return `粵拼查詢「${(parsed as JyutpingFragmentQuery).raw_q}」`;
  }
  if (parsed.kind === QueryKind.HYBRID_TAIL_EQUALS_ALIAS) {
    return `碼夾等號查詢「${(parsed as HybridTailEqualsAliasQuery).raw_q}」`;
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
  return summaryFromMatchSpec(spec, parsed);
}

function summaryFromMatchSpec(spec: MatchSpec, _parsed: ParsedQuery): string | null {
  let working = spec;
  if (working.extra?.dual_phoneme) {
    const dual = working.extra.dual_final_spec;
    if (dual && typeof dual === 'object') {
      working = dual as MatchSpec;
    }
  }

  if (working.hybrid_ref_chars && working.hybrid_ref_chars.length > 1) {
    return hybridMultiCharSummary(working);
  }

  const equals = getEqualsSpan(working);
  if (equals && working.extra?.prefix_wildcard_equals) {
    return prefixWildcardEqualsSummary(working, equals);
  }
  if (equals?.whole_word) {
    return wholeWordEqualsSummary(working, equals);
  }
  if (working.compound_kind) {
    return compoundSummary(working);
  }
  return slotScanSummary(working, equals);
}

function wholeWordEqualsSummary(spec: MatchSpec, equals: EqualsSpan): string {
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const line = `整詞同「${equals.ref_literal}」${dim}（${label}）`;
  const codePhrase = codePrefixPhrase(spec);
  return codePhrase ? `${line}；${codePhrase}` : line;
}

function prefixWildcardEqualsSummary(spec: MatchSpec, equals: EqualsSpan): string {
  const dim = rhymeOrInitial(equals.dimension);
  const label = rhymeLabel(equals.ref_literal.length);
  const positions = Array.from({ length: spec.width - equals.start_pos }, (_, i) => equals.start_pos + i);
  const posLabel = posListLabel(positions);
  return `首個字任意；${posLabel}同「${equals.ref_literal}」${dim}（${label}）`;
}

function hybridMultiCharSummary(spec: MatchSpec): string {
  const ref = spec.hybrid_ref_chars || '';
  const parts = [widthLabel(spec.width)];
  const scan = slotScanDetails(spec, null);
  if (scan) {
    parts.push(scan);
  }
  parts.push(`字面含「${ref}」`);
  return parts.length > 2
    ? `${parts[0]}：${parts[1]}，${parts.slice(2).join('，')}`
    : `${parts[0]}：${parts[1] ?? ''}`;
}

function compoundSummary(spec: MatchSpec): string {
  if (spec.compound_kind === 'doubled_syllable') {
    const rhyme = (spec.slots ?? []).find(
      (s) => s.kind === 'final_anchor' && typeof s.value === 'string',
    )?.value as string | undefined;
    if (spec.code_prefix && rhyme) {
      return `查二字同音節疊字（碼 ${spec.code_prefix}，尾字同「${rhyme}」同韻）`;
    }
    if (spec.code_prefix) {
      return `查二字同音節疊字（碼 ${spec.code_prefix}）`;
    }
    if (rhyme) {
      return `查二字同音節疊字（尾字同「${rhyme}」同韻）`;
    }
    return '查二字同音節疊字（兩字音節相同，聲調不限）';
  }
  const label = spec.compound_kind === 'syn' ? '近義' : '反義';
  const connective = spec.extra?.connective;
  if (typeof connective === 'string' && connective) {
    return `查詢含「${connective}」嘅${label}複合詞`;
  }
  return `查詢${label}複合詞`;
}

function codePrefixPhrase(spec: MatchSpec): string | null {
  if (!spec.code_prefix) {
    return null;
  }
  if (spec.width === spec.code_prefix.length) {
    const parts = [...spec.code_prefix].map((digit, i) => `${wordPos(i)}同 ${digit} 同音`);
    return parts.join('，');
  }
  return `前 ${spec.code_prefix.length} 個字為碼 ${spec.code_prefix}`;
}

function slotScanSummary(spec: MatchSpec, equals: EqualsSpan | null): string {
  const details = slotScanDetails(spec, equals);
  if (!details) {
    return widthLabel(spec.width);
  }
  return `${widthLabel(spec.width)}：${details}`;
}

function slotScanDetails(spec: MatchSpec, equals: EqualsSpan | null): string {
  const constraints = effectiveConstraints(spec, equals);
  const phrases = [...constraints.entries()]
    .sort(([a], [b]) => a - b)
    .map(([pos, [kind, value]]) => constraintPhrase(pos, kind, value));
  return phrases.join('，');
}

function effectiveConstraints(
  spec: MatchSpec,
  equals: EqualsSpan | null,
): Map<number, [string, string]> {
  const result = new Map<number, [string, string]>();

  if (spec.code_prefix && spec.width === spec.code_prefix.length) {
    for (let i = 0; i < spec.code_prefix.length; i++) {
      result.set(i, ['code_digit', spec.code_prefix[i]!]);
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
    if (
      existing &&
      (SLOT_PRIORITY[existing[0]] ?? 0) >= (SLOT_PRIORITY[slot.kind] ?? 0)
    ) {
      continue;
    }
    result.set(slot.pos, [slot.kind, value]);
  }

  if (equals && !equals.whole_word) {
    const dimKind = equals.dimension === 'final' || equals.dimension === 'rhyme'
      ? 'final_anchor'
      : 'initial_anchor';
    for (let i = 0; i < equals.ref_literal.length; i++) {
      const pos = equals.start_pos + i;
      if (pos < 0 || pos >= spec.width) {
        continue;
      }
      const digit =
        spec.code_prefix && pos < spec.code_prefix.length
          ? spec.code_prefix[pos]
          : undefined;
      if (equals.phoneme_anchor_only && digit != null) {
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

  if (spec.hybrid_ref_chars && spec.hybrid_ref_chars.length === 1) {
    const pos = spec.hybrid_ref_pos ?? 0;
    const ref = spec.hybrid_ref_chars;
    const existing = result.get(pos);
    if (existing?.[0] === 'code_digit') {
      result.set(pos, ['hybrid_tail_rhyme', `${existing[1]}|${ref}`]);
    } else {
      result.set(pos, ['final_anchor', ref]);
    }
  }

  return result;
}

function constraintPhrase(pos: number, kind: string, value: string): string {
  const label = wordPos(pos);
  if (kind === 'code_digit') {
    return `${label}同 ${value} 同音`;
  }
  if (kind === 'literal_char') {
    return `${label}為「${value}」`;
  }
  if (kind === 'wildcard') {
    return `${label}任意字`;
  }
  if (kind === 'hybrid_tail_rhyme') {
    const [digit, ref] = value.split('|', 2);
    return `${label}同 ${digit} 同音且同「${ref}」同韻`;
  }
  if (kind === 'hybrid_tail_initial') {
    const [digit, ref] = value.split('|', 2);
    return `${label}同 ${digit} 同音且同「${ref}」同聲`;
  }
  if (kind === 'final_anchor') {
    return `${label}同「${value}」同韻`;
  }
  if (kind === 'initial_anchor') {
    return `${label}同「${value}」同聲`;
  }
  if (kind === 'rhyme_letters') {
    return `${label}同韻母 ${value}`;
  }
  if (kind === 'initial_letters') {
    return `${label}同聲母 ${value}`;
  }
  if (kind === 'syllable_letters') {
    return `${label}粵拼音節 ${value}`;
  }
  return `${label}為「${value}」`;
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
}
