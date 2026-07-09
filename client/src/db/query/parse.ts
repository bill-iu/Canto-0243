/**
 * Canto-0243 Browser Query Engine
 * Port of Python query engine to JavaScript/TypeScript
 * 
 * This module implements the core query logic from the Python backend
 * to enable full client-side search functionality in the browser.
 */

import { ensureStaticRelationIndexes, getDatabase, initializeDatabase, isDatabaseInitialized } from '../init.ts';
import type { Database } from '../sqljs.ts';
import { queryFirst, queryRows } from '../database-backend.ts';
import { getCodeVariants } from '../code-variants.ts';
import {
  codeMatchesPingZePattern,
  isPingZeSerialQuery,
  pingZeEffectiveMode,
  pingZeModeRedirectHint,
  tryParsePingZeSerial,
} from '../ping-zak.ts';
import { sortQueryResults, sortWordRows, compareSearchResults, literalPriorityCompare } from '../ranking.ts';
import { searchCompoundTiers } from '../compound.ts';
import { executeHeteronymCodeSearch } from '../heteronym.ts';
import { relationLookupItems, relationPoolPage, type RelationPoolItem } from '../relation-pool.ts';
import { parseJyutpingAnchorQuery as parseJyutpingAnchorFields } from '../jyutping-anchor.ts';
import { rhymeFinalsFromJyutping } from '../jyutping-codec.ts';
import {
  expectedWordLength,
  isJyutpingQuery,
  matchesJyutpingQuery,
} from '../jyutping-match.ts';
import {
  getEqualsSpan,
  type CandidateSource,
  type CompoundKind,
  type ConstraintKind,
  type EqualsDimension,
  type EqualsSpan,
  type MaskFamilySearchResult,
  type MatchSpec,
  type SlotConstraint,
} from '../position-match/spec.ts';
import { isWildcardChar } from '../position-match/mask-grammar.ts';
import { compoundSearchSpecFromMatchSpec, getCandidatesForLength } from '../position-match/sources.ts';
import { executeMatchSpec, filterMatchSpecRows } from '../position-match/engine.ts';
import { maskFromCanonicalPlusQuery } from '../plus-grammar.ts';
import { defaultSyllableLettersForAnchorChar } from '../rime-index.ts';
import { normalizeToMatchSpec } from '../position-match/match-spec-registry.ts';
import { getWordText } from '../position-match/word-row.ts';
import { QueryKind, RouteKind } from '../query-kind.ts';
import { routeKindFor } from '../query-kind-registry.ts';
import { FILLWORD_CONNECTIVES } from '../_generated/fillword-connectives.ts';
import type {
  CodeRefMiddleRhymeQuery,
  CompoundAntQuery,
  CompoundDoubledSyllableQuery,
  CompoundSynQuery,
  DigitCodeQuery,
  PingZeSerialQuery,
  HeteronymCodeQuery,
  JyutpingAnchorQuery,
  JyutpingFragmentQuery,
  LiteralRefQuery,
  MaskQuery,
  ParsedQuery,
  PartialInitialMaskQuery,
  PartialRhymeMaskQuery,
  PlusAnchorQuery,
  PrefixWildcardEqualsQuery,
  QueryMode,
  QueryResult,
  RelationLookupQuery,
  RhymeAnchorQuery,
  SearchContext,
  SearchResult,
  SerialPhonemeAnchorQuery,
  TripleRhymeAnchorQuery,
  UnmatchedQuery,
  WildcardCodeAnchorQuery,
  WordLookupQuery,
} from '../query-types.ts';


// --- parse (query_parse port) ---
// ============================================================================
// Query Types and Constants
// ============================================================================

export { QueryKind, RouteKind } from '../query-kind.ts';

const DOUBLED_SYLLABLE_MIN_DOLLARS = 2;
const DOUBLED_SYLLABLE_MAX_DOLLARS = 4;
const DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT = '雙聲疊韻字查詢須用 2 至 4 個連續 $。';
const DOUBLED_SYLLABLE_CODE_WIDTH_HINT = '碼位數須與 $ 個數一致（如 333$$$）。';

/** Map lyrics.db row (`char`) to UI-facing QueryResult (`word`). */
export function rowToResult(row: Record<string, unknown>): QueryResult {
  const item: QueryResult = {
    word: String(row.char ?? ''),
    jyutping: String(row.jyutping ?? ''),
    code: String(row.code ?? ''),
    score: 0,
  };
  const dim = row.anchor_dimension;
  if (dim === 'initial' || dim === 'final') {
    item.anchor_dimension = dim;
  }
  return item;
}

export async function sortMaskFamilyRows(
  spec: MatchSpec,
  rows: WordRow[],
  db: Database,
  _mode: QueryMode,
): Promise<WordRow[]> {
  if (spec.extra?.dual_phoneme) {
    return rows;
  }
  const literalPositions = spec.extra?.literal_positions;
  if (spec.literal_priority && Array.isArray(literalPositions) && literalPositions.length) {
    const positions = literalPositions as Array<[number, string]>;
    return [...rows].sort((a, b) => literalPriorityCompare(a, b, positions));
  }
  if (spec.compound_kind) {
    const compoundSpec = compoundSearchSpecFromMatchSpec(spec);
    if (!compoundSpec) {
      return sortWordRows(rows);
    }
    const tiers = await searchCompoundTiers(db, compoundSpec);
    return [...rows].sort((a, b) => {
      const ta = tiers.get(getWordText(a)) ?? 99;
      const tb = tiers.get(getWordText(b)) ?? 99;
      if (ta !== tb) {
        return ta - tb;
      }
      return compareSearchResults(a, b);
    });
  }
  return sortWordRows(rows);
}

// ============================================================================
// Query Normalization and Parsing (from query_parse.py)
// ============================================================================

/**
 * Normalize query string:
 * - Strip whitespace
 * - Handle code tail normalization
 * - Full-width punctuation normalization
 */
export function normalizeQuery(q: string): string {
  if (!q) return q;
  
  // Strip whitespace
  let normalized = q.trim();
  
  // Convert full-width punctuation to half-width
  // Full-width: ！＠＃＄％＆＊（）＋－＝７８？、。
  // Half-width: !@#$%&*()+-=78?,.
  const fullToHalf: Record<string, string> = {
    '！': '!', '＠': '@', '＃': '#', '＄': '$', '％': '%',
    '＆': '&', '＊': '*', '（': '(', '）': ')', '＋': '+',
    '－': '-', '＝': '=', '７': '7', '８': '8', '？': '?',
    '、': ',', '。': '.',
  };
  
  normalized = normalized.replace(/[！＠＃＄％＆＊（）＋－＝７８？、。]/g, (match) => fullToHalf[match] || match);
  normalized = normalized.replace(/～～/g, '~~').replace(/！！/g, '!!');

  normalized = normalizeHanziDollarSyllableAnchors(normalized);
  return normalizeCodeSandwichTailEquals(normalized);
}

/** Port of query_lexer.normalize_code_sandwich_tail_equals (ADR-0028) */
function normalizeCodeSandwichTailEquals(q: string): string {
  if (!q || q.includes('=')) {
    return q;
  }
  if (/^(\d+)([\u4e00-\u9fff]+)$/.test(q)) {
    return `${q}=`;
  }
  return q;
}

/** Port of jyutping_anchor.normalize_hanzi_dollar_syllable_anchors */
function normalizeHanziDollarSyllableAnchors(q: string): string {
  if (!q || !q.includes('$')) {
    return q;
  }
  const out: string[] = [];
  let i = 0;
  while (i < q.length) {
    if (q[i] === '$') {
      let j = i;
      while (j < q.length && q[j] === '$') {
        j += 1;
      }
      if (j - i >= 2) {
        out.push(q.slice(i, j));
        i = j;
        continue;
      }
    }
    if (
      q[i] === '$' &&
      i + 1 < q.length &&
      /^[\u4e00-\u9fff]$/.test(q[i + 1]!)
    ) {
      const letters = defaultSyllableLettersForAnchorChar(q[i + 1]!);
      if (letters) {
        out.push(letters);
        i += 2;
        continue;
      }
    }
    out.push(q[i]!);
    i += 1;
  }
  return out.join('');
}

/**
 * Check if query is pure digits
 */
function isPureDigits(q: string): boolean {
  return /^\d+$/.test(q);
}

/**
 * Check if query contains Chinese characters
 */
function hasChineseChars(q: string): boolean {
  return /[\u4e00-\u9fff]/.test(q);
}

/**
 * Check if query looks like jyutping (contains letters)
 */
function hasJyutpingChars(q: string): boolean {
  return /[a-zA-Z]/.test(q);
}

/** ponytail: Python CODE_TAIL_MIDDLE is `+`; TS legacy uses ∕ for plus-anchor only */
const GRAMMAR_PLUS = '+';

/** Port of heteronym.parse_heteronym_code_query */
export function parseHeteronymCodeQuery(q: string): HeteronymCodeQuery | UnmatchedQuery | null {
  if (!q || q.includes('$') || /[\u4e00-\u9fff]/.test(q)) {
    return null;
  }
  const m = q.match(/^([\d?]+)\/([\d?]+)$/);
  if (!m) {
    return null;
  }
  const left = m[1]!;
  const right = m[2]!;
  if (left.length !== right.length) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: '同音異讀查詢左右碼位模板須等長。',
    };
  }
  return {
    kind: QueryKind.HETERONYM_CODE,
    raw_q: q,
    left_template: left,
    right_template: right,
    width: left.length,
  };
}

/** Port of relation.parse_doubled_syllable_syntax */
export function parseDoubledSyllableSyntax(
  q: string,
): CompoundDoubledSyllableQuery | UnmatchedQuery | null {
  const m = q.match(/^(\d*)(\$+)([\u4e00-\u9fff])?$/);
  if (!m) {
    return null;
  }
  const width = m[2]!.length;
  if (width < DOUBLED_SYLLABLE_MIN_DOLLARS || width > DOUBLED_SYLLABLE_MAX_DOLLARS) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT,
    };
  }
  const prefix = m[1] ?? '';
  if (prefix && prefix.length !== width) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: DOUBLED_SYLLABLE_CODE_WIDTH_HINT,
    };
  }
  return {
    kind: QueryKind.COMPOUND_DOUBLED_SYLLABLE,
    raw_q: q,
    width,
    code_prefix: prefix || undefined,
    rhyme_char: m[3] || undefined,
  };
}

/** Port of relation.parse_relation_syntax (compound + single ~ / ! lookup) */
export function parseRelationSyntax(q: string): ParsedQuery | null {
  let m = q.match(
    new RegExp(`^(\\d*)~([${FILLWORD_CONNECTIVES}])~([\u4e00-\u9fff])?$`),
  );
  if (m) {
    return {
      kind: QueryKind.COMPOUND_SYN,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[3] || undefined,
    } as CompoundSynQuery;
  }

  m = q.match(
    new RegExp(`^(\\d*)!([${FILLWORD_CONNECTIVES}])!([\u4e00-\u9fff])?$`),
  );
  if (m) {
    return {
      kind: QueryKind.COMPOUND_ANT,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[3] || undefined,
    } as CompoundAntQuery;
  }

  m = q.match(/^(\d*)~~([\u4e00-\u9fff])?$/);
  if (m) {
    return {
      kind: QueryKind.COMPOUND_SYN,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[2] || undefined,
    } as CompoundSynQuery;
  }

  m = q.match(/^(\d*)!!([\u4e00-\u9fff])?$/);
  if (m) {
    return {
      kind: QueryKind.COMPOUND_ANT,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[2] || undefined,
    } as CompoundAntQuery;
  }

  m = q.match(/^(\d*)([~!])([\u4e00-\u9fff]+)$/);
  if (m) {
    return {
      kind: QueryKind.RELATION_LOOKUP,
      raw_q: q,
      relation_kind: m[2] === '~' ? 'syn' : 'ant',
      word: m[3]!,
      code_prefix: m[1] || undefined,
    } as RelationLookupQuery;
  }

  return null;
}

/** Port of rhyme.parse_code_ref_rhyme_contradiction_hint */
function parseCodeRefRhymeContradictionHint(q: string): string | null {
  const m = q.match(/^([?_%]+)(\d+)([\u4e00-\u9fff])([?_%])$/);
  if (m && !q.includes('=')) {
    return `碼位同參考字「${m[3]}」衝突：請改用 \`?${m[2]}${m[3]}=?\` 標中格同韻。`;
  }
  return null;
}

/** Port of rhyme.parse_code_ref_middle_rhyme_query */
export function parseCodeRefMiddleRhymeQuery(q: string): CodeRefMiddleRhymeQuery | null {
  const m = q.match(/^([?_%]+)(\d+)([\u4e00-\u9fff])=\?$/);
  if (!m) {
    return null;
  }
  const leading = m[1]!;
  const digits = m[2]!;
  const anchor = m[3]!;
  const width = leading.length + digits.length + 1;
  const anchorPos = leading.length + digits.length - 1;
  const slots: CodeRefMiddleRhymeQuery['slots'] = [];
  for (let i = 0; i < digits.length; i++) {
    slots.push({ pos: leading.length + i, kind: 'code_digit', value: digits[i] });
  }
  slots.push({ pos: anchorPos, kind: 'final_anchor', value: anchor });
  return {
    kind: QueryKind.CODE_REF_MIDDLE_RHYME,
    raw_q: q,
    width,
    anchor,
    anchor_pos: anchorPos,
    leading,
    digits,
    slots,
  };
}

/** Port of rhyme.parse_double_wildcard_rhyme_query */
function parseDoubleWildcardRhymeQuery(q: string): RhymeAnchorQuery | null {
  const m = q.match(/^([?_%])\+([\u4e00-\u9fff])=$/);
  if (!m) {
    return null;
  }
  return {
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    constraint: 'final',
    anchor: m[2]!,
    anchor_pos: 1,
    slots: m[1]!,
    width: 2,
  };
}

/** Port of rhyme.parse_double_wildcard_initial_query */
function parseDoubleWildcardInitialQuery(q: string): RhymeAnchorQuery | null {
  const m = q.match(/^([?_%])\+=([\u4e00-\u9fff])$/);
  if (!m) {
    return null;
  }
  return {
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    constraint: 'initial',
    anchor: m[2]!,
    anchor_pos: 1,
    slots: m[1]!,
    width: 2,
  };
}

/** Port of rhyme.parse_triple_rhyme_anchor_query */
export function parseTripleRhymeAnchorQuery(q: string): TripleRhymeAnchorQuery | null {
  if (!q || q.includes('@') || isFramedEqualsQuery(q)) {
    return null;
  }

  let m = q.match(/^(\?\+)([\u4e00-\u9fff])=\?$/);
  if (m) {
    return {
      kind: QueryKind.TRIPLE_RHYME_ANCHOR,
      raw_q: q,
      anchor: m[2]!,
      anchor_pos: 1,
      width: 3,
      leading_slots: m[1]!,
      constraint: 'final',
    };
  }

  if (q.includes('+') || q.includes(CODE_TAIL_MIDDLE)) {
    return null;
  }

  m = q.match(/^([0-9_?%]+)([\u4e00-\u9fff])=\?$/);
  if (!m) {
    return null;
  }
  const leading = m[1]!;
  const anchor = m[2]!;
  if (![...leading].some((c) => isWildcardChar(c))) {
    return null;
  }
  if (/\d/.test(leading)) {
    return null;
  }
  const anchorPos = leading.length;
  return {
    kind: QueryKind.TRIPLE_RHYME_ANCHOR,
    raw_q: q,
    anchor,
    anchor_pos: anchorPos,
    width: anchorPos + 2,
    leading_slots: leading,
    constraint: 'final',
  };
}

function wcaTokenize(body: string): Array<[string, string]> | null {
  const tokens: Array<[string, string]> = [];
  let i = 0;
  while (i < body.length) {
    const ch = body[i]!;
    if (isWildcardChar(ch)) {
      tokens.push(['wild', ch]);
      i += 1;
    } else if (ch === GRAMMAR_PLUS || ch === CODE_TAIL_MIDDLE) {
      tokens.push(['star', '']);
      i += 1;
    } else if (/\d/.test(ch)) {
      while (i < body.length && /\d/.test(body[i]!)) {
        tokens.push(['code', body[i]!]);
        i += 1;
      }
    } else if (/[\u4e00-\u9fff]/.test(ch)) {
      tokens.push(['ref', ch]);
      i += 1;
    } else {
      return null;
    }
  }
  return tokens.length ? tokens : null;
}

function wcaTokensToSpec(
  tokens: Array<[string, string]>,
  headLiteral?: string,
): Omit<WildcardCodeAnchorQuery, 'kind' | 'raw_q'> | null {
  const syllables: Array<Record<string, string | boolean>> = [];
  if (headLiteral) {
    syllables.push({ literal: headLiteral });
  }
  let i = 0;
  while (i < tokens.length) {
    const [kind, val] = tokens[i]!;
    if (kind === 'wild') {
      syllables.push({ wild: true });
      i += 1;
    } else if (kind === 'code') {
      syllables.push({ code: val });
      i += 1;
    } else if (kind === 'star') {
      if (i + 1 < tokens.length && tokens[i + 1]![0] === 'ref') {
        syllables.push({ ref: tokens[i + 1]![1], star_before: true });
        i += 2;
      } else {
        syllables.push({ wild: true });
        i += 1;
      }
    } else if (kind === 'ref') {
      const last = syllables[syllables.length - 1];
      if (last && 'code' in last && !('ref' in last)) {
        last.ref = val;
        i += 1;
      } else {
        return null;
      }
    } else {
      return null;
    }
  }
  if (!syllables.length) {
    return null;
  }
  if (!syllables.some((s) => 'code' in s) || !syllables.some((s) => 'ref' in s)) {
    return null;
  }
  if (!headLiteral && !(tokens[0] && tokens[0][0] === 'wild')) {
    return null;
  }
  const slots: WildcardCodeAnchorQuery['slots'] = [];
  for (let pos = 0; pos < syllables.length; pos++) {
    const syl = syllables[pos]!;
    if ('literal' in syl) {
      slots.push({ pos, kind: 'literal_char', value: String(syl.literal) });
    }
    if ('code' in syl) {
      slots.push({ pos, kind: 'code_digit', value: String(syl.code) });
    }
    if ('ref' in syl) {
      slots.push({ pos, kind: 'final_anchor', value: String(syl.ref) });
    }
  }
  return { width: syllables.length, slots, head_literal: headLiteral };
}

/** Port of wca.parse_wildcard_code_anchor_query */
export function parseWildcardCodeAnchorQuery(q: string): WildcardCodeAnchorQuery | null {
  if (!q || q.includes('@') || q.includes('=')) {
    return null;
  }
  if (/^\d+\+/.test(q)) {
    return null;
  }
  let m = q.match(/^\+([\u4e00-\u9fff])([?_%0-9+\u4e00-\u9fff]+)$/);
  if (m) {
    const tokens = wcaTokenize(m[2]!);
    if (!tokens) {
      return null;
    }
    const spec = wcaTokensToSpec(tokens, m[1]);
    if (!spec) {
      return null;
    }
    return { kind: QueryKind.WILDCARD_CODE_ANCHOR, raw_q: q, ...spec };
  }
  if (!'?_%'.includes(q[0]!)) {
    return null;
  }
  const tokens = wcaTokenize(q);
  if (!tokens) {
    return null;
  }
  const spec = wcaTokensToSpec(tokens);
  if (!spec) {
    return null;
  }
  return { kind: QueryKind.WILDCARD_CODE_ANCHOR, raw_q: q, ...spec };
}

/** Port of query_parse.try_parse_before_mask */
export function tryParseBeforeMask(q: string): ParsedQuery | null {
  const doubled = parseDoubledSyllableSyntax(q);
  if (doubled) {
    return doubled;
  }

  const heteronym = parseHeteronymCodeQuery(q);
  if (heteronym) {
    return heteronym;
  }

  const relationParsed = parseRelationSyntax(q);
  if (relationParsed) {
    return relationParsed;
  }

  const prefixEqHint = prefixWildcardEqualsMissingEqHint(q);
  if (prefixEqHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: prefixEqHint };
  }

  const pureCharsHint = parsePureCharsSerialHint(q);
  if (pureCharsHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: pureCharsHint };
  }

  const prefixWildcard = parsePrefixWildcardEqualsQuery(q);
  if (prefixWildcard) {
    return prefixWildcard;
  }

  const prefixInitial = parsePrefixWildcardInitialQuery(q);
  if (prefixInitial) {
    return prefixInitial;
  }

  const partialRhyme = parsePartialRhymeMaskQuery(q);
  if (partialRhyme) {
    return partialRhyme;
  }

  const partialInitial = parsePartialInitialMaskQuery(q);
  if (partialInitial) {
    return partialInitial;
  }

  const serialPhoneme = parseSerialPhonemeAnchorQuery(q);
  if (serialPhoneme) {
    return serialPhoneme;
  }

  if (isFramedEqualsQuery(q)) {
    return { kind: QueryKind.EQUALS, raw_q: q } as EqualsQuery;
  }

  const maskLiteral = maskFromCanonicalPlusQuery(q);
  if (maskLiteral) {
    return { kind: QueryKind.MASK, raw_q: maskLiteral };
  }

  const plusAnchor = parsePlusAnchorQuery(q);
  if (plusAnchor) {
    return plusAnchor;
  }

  const literalRef = parseAtTailQuery(q);
  if (literalRef) {
    return literalRef;
  }

  const contradictionHint = parseCodeRefRhymeContradictionHint(q);
  if (contradictionHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: contradictionHint };
  }

  const codeRefMiddle = parseCodeRefMiddleRhymeQuery(q);
  if (codeRefMiddle) {
    return codeRefMiddle;
  }

  const doubleWildRhyme = parseDoubleWildcardRhymeQuery(q);
  if (doubleWildRhyme) {
    return doubleWildRhyme;
  }

  const doubleWildInitial = parseDoubleWildcardInitialQuery(q);
  if (doubleWildInitial) {
    return doubleWildInitial;
  }

  const wca = parseWildcardCodeAnchorQuery(q);
  if (wca) {
    return wca;
  }

  const tripleRhyme = parseTripleRhymeAnchorQuery(q);
  if (tripleRhyme) {
    return tripleRhyme;
  }

  const jyutpingAnchor = parseJyutpingAnchorQuery(q);
  if (jyutpingAnchor) {
    return jyutpingAnchor;
  }

  const rhymeAnchor = parseRhymeAnchorQuery(q);
  if (rhymeAnchor) {
    return rhymeAnchor;
  }

  return null;
}

export const JYUTPING_SYN_MODE_HINT =
  '近反義模式只支援漢字查詢。請改打漢字，或切換至 0243模式／02493模式 查粵拼。';

export { isJyutpingQuery } from '../jyutping-match.ts';

/** Pure detect SSOT — codegen to frontend/query-mode-detect.mjs */
export {
  isPingZeSerialQuery,
  isRelationSyntaxQuery,
  normalizeQuerySyntax,
} from './mode-detect.ts';

export function resolveFallback0243Mode(fallback?: QueryMode): 'm1' | 'm2' | 'm3' {
  if (fallback === 'm3' || fallback === '394052') {
    return 'm3';
  }
  if (fallback === 'm2' || fallback === '02493') {
    return 'm2';
  }
  return 'm1';
}

import { modeRedirectHint } from '../../mode-meta.ts';
export { modeRedirectHint };

/**
 * Parse query and classify into QueryKind
 */
export function parseQuery(q: string): ParsedQuery {
  const normalized = normalizeQuery(q);

  const beforeMask = tryParseBeforeMask(normalized);
  if (beforeMask) {
    return beforeMask;
  }

  if (looksLikeMaskQuery(normalized)) {
    return { kind: QueryKind.MASK, raw_q: normalized };
  }

  const pingZeParsed = tryParsePingZeSerial(normalized);
  if (pingZeParsed) {
    return pingZeParsed;
  }

  if (isPureDigits(normalized)) {
    return { kind: QueryKind.DIGIT_CODE, raw_q: normalized };
  }

  if (hasChineseChars(normalized)) {
    return { kind: QueryKind.WORD_LOOKUP, raw_q: normalized };
  }

  if (hasJyutpingChars(normalized)) {
    return { kind: QueryKind.JYUTPING_FRAGMENT, raw_q: normalized };
  }

  return { kind: QueryKind.UNMATCHED, raw_q: normalized, hint: '無法辨認的查詢語法' };
}

/**
 * Normalize and parse query
 */
export function normalizeAndParse(q: string): ParsedQuery {
  return parseQuery(normalizeQuery(q));
}

/**
 * Mask detection — port of query_grammar/mask.looks_like_mask_query
 */
function looksLikeMaskQuery(q: string): boolean {
  if (!q || q.includes(CODE_TAIL_MIDDLE) || q.includes('@')) {
    return false;
  }
  if (!/^[0-9_?%\u4e00-\u9fff]+$/.test(q)) {
    return false;
  }
  const hasWild = [...q].some((c) => isWildcardChar(c));
  const hasDigit = /\d/.test(q);
  const hasCanto = [...q].some((c) => !/\d/.test(c) && !isWildcardChar(c));
  return hasWild || (hasDigit && hasCanto);
}

/** Port of plus.parse_at_tail_query — 碼＋@＋尾字（23@手） */
export function parseAtTailQuery(q: string): LiteralRefQuery | null {
  const m = q.match(/^(\d+)@([\u4e00-\u9fff])$/);
  if (!m) {
    return null;
  }
  const code_digits = m[1]!;
  return {
    kind: QueryKind.LITERAL_REF,
    raw_q: q,
    code_digits,
    literal_char: m[2]!,
    width: code_digits.length,
  };
}

/** Port of plus.parse_plus_anchor_query — slot connector is `+` (Python CODE_TAIL_MIDDLE) */
export function parsePlusAnchorQuery(q: string): PlusAnchorQuery | null {
  if (!q || !q.includes('+') || q.includes('@')) {
    return null;
  }

  const base = (
    fields: Omit<PlusAnchorQuery, 'kind' | 'raw_q'>,
  ): PlusAnchorQuery => ({
    kind: QueryKind.PLUS_ANCHOR,
    raw_q: q,
    ...fields,
  });

  let m = q.match(/^\+([\u4e00-\u9fff])(=)?(\d+)$/);
  if (m) {
    const anchor = m[1]!;
    const right = m[3]!;
    const width = 1 + right.length;
    return base({
      width,
      anchor_pos: 0,
      anchor,
      constraint: m[2] ? 'final' : 'literal',
      code_slots: [...right].map((d, i) => [1 + i, d] as [number, string]),
    });
  }

  m = q.match(/^(\d+)\+([\u4e00-\u9fff])(=)?(\d+)$/);
  if (m) {
    const left = m[1]!;
    const anchor = m[2]!;
    const right = m[4]!;
    const anchorPos = left.length;
    const width = left.length + 1 + right.length;
    return base({
      width,
      anchor_pos: anchorPos,
      anchor,
      constraint: m[3] ? 'final' : 'literal',
      code_slots: [
        ...[...left].map((d, i) => [i, d] as [number, string]),
        ...[...right].map((d, i) => [anchorPos + 1 + i, d] as [number, string]),
      ],
    });
  }

  m = q.match(/^(\d+)\+([\u4e00-\u9fff])(=)?$/);
  if (m) {
    const code = m[1]!;
    const anchor = m[2]!;
    const width = code.length + 1;
    return base({
      width,
      anchor_pos: width - 1,
      anchor,
      constraint: m[3] ? 'final' : 'literal',
      code_slots: [...code].map((d, i) => [i, d] as [number, string]),
      code_prefix: code,
    });
  }

  m = q.match(/^(\d+)\+=([\u4e00-\u9fff])$/);
  if (m) {
    const code = m[1]!;
    const anchor = m[2]!;
    const width = code.length + 1;
    return base({
      width,
      anchor_pos: width - 1,
      anchor,
      constraint: 'initial',
      code_slots: [...code].map((d, i) => [i, d] as [number, string]),
      code_prefix: code,
    });
  }

  return null;
}

/** ponytail: runnable self-check — `npx tsx client/scripts/parser-self-check.ts` */
export function parserLogicSelfCheck(): void {
  const cases: Array<[string, QueryKind]> = [
    ['=窮?潦倒', QueryKind.PARTIAL_INITIAL_MASK],
    ['04困=49倒=', QueryKind.SERIAL_PHONEME],
    ['?yut?', QueryKind.JYUTPING_ANCHOR],
    ['3m4', QueryKind.JYUTPING_ANCHOR],
    ['?hon', QueryKind.JYUTPING_ANCHOR],
    ['3+hon4', QueryKind.JYUTPING_ANCHOR],
    ['23o', QueryKind.JYUTPING_ANCHOR],
    ['3hon4', QueryKind.JYUTPING_ANCHOR],
    ['3$漢4', QueryKind.JYUTPING_ANCHOR],
    ['3+ngo4', QueryKind.JYUTPING_ANCHOR],
    ['23+o', QueryKind.JYUTPING_ANCHOR],
    ['就=', QueryKind.RHYME_ANCHOR],
    ['?+就=', QueryKind.RHYME_ANCHOR],
    ['?+人=?', QueryKind.TRIPLE_RHYME_ANCHOR],
    ['?30人', QueryKind.WILDCARD_CODE_ANCHOR],
    ['12/12', QueryKind.HETERONYM_CODE],
    ['33~與~你', QueryKind.COMPOUND_SYN],
    ['?=困潦倒', QueryKind.PREFIX_WILDCARD_EQUALS],
    ['$$$', QueryKind.COMPOUND_DOUBLED_SYLLABLE],
  ];
  for (const [q, kind] of cases) {
    const parsed = normalizeAndParse(q);
    if (parsed.kind !== kind) {
      throw new Error(`parserLogicSelfCheck: ${q} → ${parsed.kind}, want ${kind}`);
    }
  }
  const codeRef = parseCodeRefMiddleRhymeQuery('?3人=?');
  if (!codeRef || codeRef.anchor !== '人' || codeRef.width !== 3) {
    throw new Error('parserLogicSelfCheck: code_ref_middle parse');
  }
  const missingEq = normalizeAndParse('?困潦倒');
  if (missingEq.kind !== QueryKind.UNMATCHED || !missingEq.hint?.includes('尾格')) {
    throw new Error('parserLogicSelfCheck: prefix wildcard missing = hint');
  }
}

/** ponytail: runnable self-check — `npx tsx client/scripts/lookup-layout-self-check.ts` */
export async function lookupLayoutSelfCheck(): Promise<void> {
  const { buildLookupLayout } = await import('./lookup-layout.ts');
  const rows: WordRow[] = [
    { char: '事業', code: '22', jyutping: 'si6 jip6' },
  ];
  const layout = await buildLookupLayout('事業', rows, null);
  const words = layout.map((r) => r.word);
  if (words.length !== 1 || words[0] !== '事業') {
    throw new Error(`lookupLayoutSelfCheck: got ${words.join(',')}`);
  }
  if (layout.some((r) => r.resultType === 'code' || r.resultType === 'jyutping')) {
    throw new Error('lookupLayoutSelfCheck: must not emit code/jyutping headers');
  }
}

const SLOT_CHAR_RE = /[0-9_?%]/;

function isSlotChar(ch: string): boolean {
  return ch.length === 1 && SLOT_CHAR_RE.test(ch);
}

/** Port of query_grammar/serial.parse_prefix_wildcard_equals_query */
export function parsePrefixWildcardEqualsQuery(q: string): PrefixWildcardEqualsQuery | null {
  const m = q.match(/^\?([\u4e00-\u9fff]{2,})=$/);
  if (!m) {
    return null;
  }
  const ref = m[1]!;
  return {
    kind: QueryKind.PREFIX_WILDCARD_EQUALS,
    raw_q: q,
    inner_q: `${ref}=`,
    ref_literal: ref,
    width: ref.length + 1,
  };
}

/** Port of query_grammar/serial.parse_prefix_wildcard_initial_query */
export function parsePrefixWildcardInitialQuery(q: string): PrefixWildcardEqualsQuery | null {
  const m = q.match(/^\?=([\u4e00-\u9fff]{2,})$/);
  if (!m) {
    return null;
  }
  const ref = m[1]!;
  return {
    kind: QueryKind.PREFIX_WILDCARD_EQUALS,
    raw_q: q,
    inner_q: `=${ref}`,
    ref_literal: ref,
    width: ref.length + 1,
  };
}

const PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT =
  '前綴通配等號查詢須以 `=` 結尾。例：`?困潦倒=`（唔好漏尾格 `=`）。';
const PURE_CHARS_SERIAL_HINT =
  '每個 `{字}=`／`={字}` 前須有 0243 碼。例：`04困=49倒=`（唔好寫 `窮困=潦倒=`）。';

/** Port of serial.prefix_wildcard_equals_missing_eq_hint */
function prefixWildcardEqualsMissingEqHint(q: string): string | null {
  if (/^\?[\u4e00-\u9fff]{3,}$/.test(q)) {
    return PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT;
  }
  return null;
}

/** Port of serial.parse_pure_chars_serial_hint */
function parsePureCharsSerialHint(q: string): string | null {
  if (!q || !/^[\u4e00-\u9fff=]+$/.test(q)) {
    return null;
  }
  if (/^[\u4e00-\u9fff]=$/.test(q)) {
    return null;
  }
  if (isFramedEqualsQuery(q)) {
    return null;
  }
  if (/(?<![0-9])([\u4e00-\u9fff])=/.test(q)) {
    return PURE_CHARS_SERIAL_HINT;
  }
  return null;
}

/** Port of rhyme.normalize_partial_rhyme_mask_query */
function normalizePartialRhymeMaskQuery(q: string): string {
  const m = q.match(/^([\u4e00-\u9fff]{3})=\?$/);
  if (m) {
    return `${m[1]}?=`;
  }
  return q;
}

/** Port of rhyme.parse_partial_rhyme_mask_query */
export function parsePartialRhymeMaskQuery(q: string): PartialRhymeMaskQuery | null {
  const nq = normalizePartialRhymeMaskQuery(q);
  const m = nq.match(/^([\u4e00-\u9fff?]{4})=$/);
  if (!m) {
    return null;
  }
  const pattern = m[1]!;
  if (!pattern.includes('?') || pattern.split('').every((ch) => ch === '?')) {
    return null;
  }
  if (pattern.startsWith('?') && /^\?[\u4e00-\u9fff]{3}$/.test(pattern)) {
    return null;
  }
  const anchors: Array<[number, string]> = [];
  for (let pos = 0; pos < pattern.length; pos++) {
    const ch = pattern[pos]!;
    if (ch !== '?') {
      anchors.push([pos, ch]);
    }
  }
  if (!anchors.length) {
    return null;
  }
  return {
    kind: QueryKind.PARTIAL_RHYME_MASK,
    raw_q: q,
    pattern,
    width: 4,
    anchors,
  };
}

/** Port of rhyme.parse_partial_initial_mask_query */
export function parsePartialInitialMaskQuery(q: string): PartialInitialMaskQuery | null {
  const m = q.match(/^=([\u4e00-\u9fff?]{4})$/);
  if (!m) {
    return null;
  }
  const pattern = m[1]!;
  if (!pattern.includes('?') || pattern.split('').every((ch) => ch === '?')) {
    return null;
  }
  if (pattern.startsWith('?') && /^\?[\u4e00-\u9fff]{3}$/.test(pattern)) {
    return null;
  }
  const anchors: Array<[number, string]> = [];
  for (let pos = 0; pos < pattern.length; pos++) {
    const ch = pattern[pos]!;
    if (ch !== '?') {
      anchors.push([pos, ch]);
    }
  }
  if (!anchors.length) {
    return null;
  }
  return {
    kind: QueryKind.PARTIAL_INITIAL_MASK,
    raw_q: q,
    pattern,
    width: 4,
    anchors,
  };
}

const SERIAL_CHARSET_RE = /^[0-9?=\u4e00-\u9fff]+$/;

function framedEqualsBlocksSerial(q: string): boolean {
  if (!isFramedEqualsQuery(q)) {
    return false;
  }
  const m = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)(=)?(\d*)$/);
  if (!m) {
    return false;
  }
  if (m[2]) {
    return true;
  }
  if (m[5]) {
    return true;
  }
  if (m[4] && (m[3]?.length ?? 0) >= 2) {
    return true;
  }
  if (m[4] && m[1] && !m[5]) {
    return true;
  }
  return false;
}

function scanSerialPhoneme(
  q: string,
  constraint: 'final' | 'initial',
): Omit<SerialPhonemeAnchorQuery, 'kind' | 'raw_q'> | null {
  let i = 0;
  let pos = 0;
  const code_slots: Array<[number, string]> = [];
  const anchors: Array<[number, string]> = [];
  const maskChars: string[] = [];

  while (i < q.length) {
    const ch = q[i]!;
    if (ch === '?') {
      maskChars.push('?');
      pos += 1;
      i += 1;
      continue;
    }
    if (/\d/.test(ch)) {
      const anchorRe =
        constraint === 'final'
          ? /^(\d)([\u4e00-\u9fff])=(?=[0-9?=]|$)/
          : /^(\d)=([\u4e00-\u9fff])(?=[0-9?=]|$)/;
      const m = q.slice(i).match(anchorRe);
      if (m) {
        code_slots.push([pos, m[1]!]);
        anchors.push([pos, m[2]!]);
        maskChars.push(m[1]!);
        pos += 1;
        i += m[0].length;
        continue;
      }
      code_slots.push([pos, ch]);
      maskChars.push(ch);
      pos += 1;
      i += 1;
      continue;
    }
    return null;
  }
  if (!anchors.length) {
    return null;
  }
  return {
    width: pos,
    constraint,
    code_slots,
    anchors,
    mask: maskChars.join(''),
  };
}

/** Port of serial.parse_serial_phoneme_anchor_query */
export function parseSerialPhonemeAnchorQuery(q: string): SerialPhonemeAnchorQuery | null {
  if (!q || !SERIAL_CHARSET_RE.test(q)) {
    return null;
  }
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes('+') || q.includes('@') || q.includes('*') || q.includes('_') || q.includes('%')) {
    return null;
  }
  if (framedEqualsBlocksSerial(q)) {
    return null;
  }
  if (/^[\u4e00-\u9fff]=$/.test(q)) {
    return null;
  }
  const hasRhyme = /\d[\u4e00-\u9fff]=/.test(q);
  const hasInitial = /\d=[\u4e00-\u9fff]/.test(q);
  if (hasRhyme && hasInitial) {
    return null;
  }
  const constraint: 'final' | 'initial' = hasRhyme ? 'final' : 'initial';
  if (!hasRhyme && !hasInitial) {
    return null;
  }
  const parsed = scanSerialPhoneme(q, constraint);
  if (!parsed) {
    return null;
  }
  return { kind: QueryKind.SERIAL_PHONEME, raw_q: q, ...parsed };
}


/** Port of jyutping_anchor.parse_jyutping_anchor_query */
export function parseJyutpingAnchorQuery(q: string): JyutpingAnchorQuery | null {
  const fields = parseJyutpingAnchorFields(q);
  if (!fields) {
    return null;
  }
  return { kind: QueryKind.JYUTPING_ANCHOR, ...fields };
}

/** Port of query_grammar/rhyme.parse_rhyme_anchor_query (P1 subset) */
export function parseRhymeAnchorQuery(q: string): RhymeAnchorQuery | null {
  if (!q || q.includes(CODE_TAIL_MIDDLE) || q.includes('+') || q.includes('@') || isFramedEqualsQuery(q)) {
    return null;
  }
  if (parseDoubleWildcardRhymeQuery(q) || parseDoubleWildcardInitialQuery(q)) {
    return null;
  }

  const base = (fields: Omit<RhymeAnchorQuery, 'kind' | 'raw_q'>): RhymeAnchorQuery => ({
    kind: QueryKind.RHYME_ANCHOR,
    raw_q: q,
    ...fields,
  });

  let m = q.match(/^([\u4e00-\u9fff])=$/);
  if (m) {
    return base({
      constraint: 'final',
      anchor: m[1]!,
      anchor_pos: 0,
      slots: '',
      width: 1,
    });
  }

  m = q.match(/^=([\u4e00-\u9fff])$/);
  if (m) {
    return base({
      constraint: 'initial',
      anchor: m[1]!,
      anchor_pos: 0,
      slots: '',
      width: 1,
    });
  }

  m = q.match(/^([0-9_?%]+)([\u4e00-\u9fff])=$/);
  if (m) {
    const slots = m[1]!;
    return base({
      constraint: 'final',
      anchor: m[2]!,
      anchor_pos: slots.length,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^([\u4e00-\u9fff])=([0-9_?%]+)$/);
  if (m) {
    const slots = m[2]!;
    return base({
      constraint: 'final',
      anchor: m[1]!,
      anchor_pos: 0,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^=([\u4e00-\u9fff])([0-9_?%]+)$/);
  if (m) {
    const slots = m[2]!;
    return base({
      constraint: 'initial',
      anchor: m[1]!,
      anchor_pos: 0,
      slots,
      width: slots.length + 1,
    });
  }

  m = q.match(/^([0-9_?%]+)=([\u4e00-\u9fff])$/);
  if (m) {
    const slots = m[1]!;
    return base({
      constraint: 'initial',
      anchor: m[2]!,
      anchor_pos: slots.length,
      slots,
      width: slots.length + 1,
    });
  }

  return null;
}

// ============================================================================
// Equals Query Support (from query_grammar/equals.py)
// ============================================================================

/**
 * Constants for equals query processing
 */
export const CODE_TAIL_MIDDLE = '\u2215'; // Division slash (∕)

/**
 * Equals query interface
 */
export interface EqualsQuery extends ParsedQuery {
  kind: QueryKind.EQUALS;
  raw_q: string;
}

/**
 * Check if query is a framed equals query
 * e.g., "香港=", "2=我3", "=香", "就="
 */
export function isFramedEqualsQuery(q: string): boolean {
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes('@')) {
    return false;
  }
  
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)(=)?(\d*)$/);
  if (!match) {
    return false;
  }
  
  const target = match[3] || '';
  if (!target) {
    return false;
  }
  
  const left_code = match[1] || '';
  const right_code = match[5] || '';
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  
  // Right equal with multi-char target or single char with left code
  if (right_equal && target.length >= 2) {
    return true;
  }
  if (right_equal && left_code && target.length === 1) {
    return true;
  }
  // Inner equal cases
  if (inner_equal && left_code && right_code) {
    return true;
  }
  if (inner_equal && left_code && !right_equal) {
    return true;
  }
  if (inner_equal && !left_code && !right_equal && target.length >= 2) {
    return true;
  }
  
  return false;
}

/**
 * Hint message for code-prefixed whole word equals empty results
 */
export const CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT = 
  '「{literal}」有收錄，但在 0243 碼 {code} 下無整詞同韻結果。';

/**
 * Generate hint for empty results in code-prefixed whole word equals query
 */
export async function codePrefixedWholeWordEqualsEmptyHint(
  spec: MatchSpec,
  db: Database
): Promise<string | null> {
  const span = getEqualsSpan(spec);
  if (!span || !span.whole_word) {
    return null;
  }
  
  const { codeDigitStringFromSpec } = await import('../position-match/filters/f1-slot-code.ts');
  const code = codeDigitStringFromSpec(spec) || '';
  const literal = span.ref_literal;
  
  if (!code || code.length !== literal.length) {
    return null;
  }

  // Check if the literal exists in the database
  const sql = 'SELECT COUNT(*) as count FROM words WHERE char = ?';
  const result = await queryFirst(db, sql, [literal]) ?? { count: 0 };
  
  if (result.count === 0) {
    return null;
  }
  
  // Literal exists but no results - generate hint
  return CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT
    .replace('{literal}', literal)
    .replace('{code}', code);
}

// ============================================================================
