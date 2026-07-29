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
import { compileParsedQuery } from './position-match/compiler.ts';
import {
  buildExplainIr,
  explainIrForQuery,
  type CodePrefixIr,
  type CompoundIr,
  type EqualsIr,
  type ExplainIr,
  type ExplainIrVariant,
  type PositionConstraintIr,
} from './query-explain-ir.ts';
import { renderExplainIr, widthLabel } from './query-explain-render.ts';

export type {
  CodePrefixIr,
  CompoundIr,
  EqualsIr,
  ExplainIr,
  ExplainIrVariant,
  PositionConstraintIr,
};

export interface QueryExplainResult {
  summary: string | null;
  warning: string | null;
  kind: string | null;
}

export { buildExplainIr, explainIrForQuery, renderExplainIr };

function hasFinalRhymeConstraint(parsed: ParsedQuery): boolean {
  const kind = parsed.kind;
  return (
    kind === QueryKind.EQUALS
    || kind === QueryKind.PREFIX_WILDCARD_EQUALS
    || kind === QueryKind.PARTIAL_RHYME_MASK
    || kind === QueryKind.SERIAL_PHONEME
    || kind === QueryKind.RHYME_ANCHOR
    || kind === QueryKind.TRIPLE_RHYME_ANCHOR
    || kind === QueryKind.JYUTPING_ANCHOR
    || kind === QueryKind.CODE_REF_MIDDLE_RHYME
    || Boolean((parsed as { rhyme_char?: string }).rhyme_char)
  );
}

export function explainQuery(
  q: string,
  mode: string = 'm1',
  rhymeProfile: string = 'exact',
): QueryExplainResult {
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
  let summary = summaryFor(parsed);
  // E1: 有同韻約束且非正韻時標明檔
  if (summary && hasFinalRhymeConstraint(parsed) && rhymeProfile && rhymeProfile !== 'exact') {
    const label =
      rhymeProfile === 'tong' ? '通韻'
        : rhymeProfile === 'nucleus' ? '腹韻'
          : rhymeProfile === 'coda' ? '尾韻'
            : '';
    if (label) summary = `${summary}（${label}）`;
  }
  return {
    summary,
    warning,
    kind: parsed.kind,
  };
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

  const spec = compileParsedQuery(parsed);
  if (!spec) {
    const raw = parsed.raw_q;
    return raw ? `查詢「${raw}」` : '查詢';
  }
  return renderExplainIr(buildExplainIr(spec, parsed));
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
