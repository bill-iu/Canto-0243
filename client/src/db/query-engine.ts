/**
 * Canto-0243 Browser Query Engine
 * Port of Python query engine to JavaScript/TypeScript
 * 
 * This module implements the core query logic from the Python backend
 * to enable full client-side search functionality in the browser.
 */

import { getDatabase, initializeDatabase, isDatabaseInitialized } from './init.ts';
import type { Database } from './sqljs.ts';
import { getCodeVariants } from './code-variants.ts';
import { sortQueryResults, sortWordRows, compareSearchResults } from './ranking.ts';
import { searchCompoundTiers } from './compound.ts';
import { executeHeteronymCodeSearch } from './heteronym.ts';
import { relationLookupItems } from './relation-pool.ts';
import { parseJyutpingAnchorQuery as parseJyutpingAnchorFields } from './jyutping-anchor.ts';
import { rhymeFinalsFromJyutping } from './jyutping-codec.ts';
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
} from './position-match/spec.ts';
import { isWildcardChar } from './position-match/mask-grammar.ts';
import { compoundSearchSpecFromMatchSpec } from './position-match/sources.ts';
import { executeMatchSpec } from './position-match/engine.ts';
import { normalizeToMatchSpec } from './position-match/match-spec-registry.ts';
import { getWordText } from './position-match/word-row.ts';
import { QueryKind, RouteKind } from './query-kind.ts';

// ============================================================================
// Query Types and Constants
// ============================================================================

export { QueryKind, RouteKind } from './query-kind.ts';

/**
 * Query modes supported by the engine
 */
export type QueryMode = 'm1' | 'm2' | '0243' | '02493' | 'syn';

/**
 * Base parsed query interface
 */
export interface ParsedQuery {
  kind: QueryKind;
  raw_q: string;
}

/**
 * Digit code query (pure numeric codes)
 */
export interface DigitCodeQuery extends ParsedQuery {
  kind: QueryKind.DIGIT_CODE;
  raw_q: string;
}

/**
 * Word lookup query (Chinese characters)
 */
export interface WordLookupQuery extends ParsedQuery {
  kind: QueryKind.WORD_LOOKUP;
  raw_q: string;
}

/**
 * Jyutping fragment query
 */
export interface JyutpingFragmentQuery extends ParsedQuery {
  kind: QueryKind.JYUTPING_FRAGMENT;
  raw_q: string;
}

/**
 * Mask query (contains wildcards)
 */
export interface MaskQuery extends ParsedQuery {
  kind: QueryKind.MASK;
  raw_q: string;
}

/** Rhyme/initial anchor query (就=, =就, 香=?, =香?) */
export interface RhymeAnchorQuery extends ParsedQuery {
  kind: QueryKind.RHYME_ANCHOR;
  raw_q: string;
  constraint: 'final' | 'initial';
  anchor_pos: number;
  anchor: string;
  slots: string;
  width: number;
}

/** Prefix wildcard equals (?困潦倒=) */
export interface PrefixWildcardEqualsQuery extends ParsedQuery {
  kind: QueryKind.PREFIX_WILDCARD_EQUALS;
  raw_q: string;
  inner_q: string;
  ref_literal: string;
  width: number;
}

/** Four-char partial rhyme mask (窮?潦倒=) */
export interface PartialRhymeMaskQuery extends ParsedQuery {
  kind: QueryKind.PARTIAL_RHYME_MASK;
  raw_q: string;
  pattern: string;
  width: number;
  anchors: Array<[number, string]>;
}

/** Four-char partial initial mask (=窮?潦倒) */
export interface PartialInitialMaskQuery extends ParsedQuery {
  kind: QueryKind.PARTIAL_INITIAL_MASK;
  raw_q: string;
  pattern: string;
  width: number;
  anchors: Array<[number, string]>;
}

/** Serial phoneme anchors (04困=49倒=) */
export interface SerialPhonemeAnchorQuery extends ParsedQuery {
  kind: QueryKind.SERIAL_PHONEME;
  raw_q: string;
  width: number;
  constraint: 'final' | 'initial';
  code_slots: Array<[number, string]>;
  anchors: Array<[number, string]>;
  mask: string;
}

/** Jyutping anchor (?yut?, 3m4, 23o, …) */
export interface JyutpingAnchorQuery extends ParsedQuery {
  kind: QueryKind.JYUTPING_ANCHOR;
  raw_q: string;
  width: number;
  anchor_pos: number;
  anchor_kind: 'initial_letters' | 'rhyme_letters' | 'syllable_letters';
  anchor_value: string;
  dual_phoneme?: boolean;
  code_prefix?: string;
  equals_style?: boolean;
  code_slots?: Array<[number, string]>;
  hybrid_rhyme?: boolean;
  dual_initial_value?: string;
}

/** Hybrid code query (23就) */
export interface HybridCodeQuery extends ParsedQuery {
  kind: QueryKind.HYBRID_CODE;
  raw_q: string;
}

/** Literal reference at tail (23@就) */
export interface LiteralRefQuery extends ParsedQuery {
  kind: QueryKind.LITERAL_REF;
  raw_q: string;
  code_digits: string;
  literal_char: string;
  width: number;
}

/** Plus anchor (23+就, 2+好3, +門0) */
export interface PlusAnchorQuery extends ParsedQuery {
  kind: QueryKind.PLUS_ANCHOR;
  raw_q: string;
  width: number;
  anchor_pos: number;
  anchor: string;
  constraint: 'literal' | 'final' | 'initial';
  code_slots: Array<[number, string]>;
  code_prefix?: string;
}

export interface CompoundSynQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_SYN;
  raw_q: string;
  code_prefix?: string;
  rhyme_char?: string;
}

export interface CompoundAntQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_ANT;
  raw_q: string;
  code_prefix?: string;
  rhyme_char?: string;
}

export interface CompoundDoubledSyllableQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_DOUBLED_SYLLABLE;
  raw_q: string;
  code_prefix?: string;
  rhyme_char?: string;
}

export interface HeteronymCodeQuery extends ParsedQuery {
  kind: QueryKind.HETERONYM_CODE;
  raw_q: string;
  left_template: string;
  right_template: string;
  width: number;
}

export interface WildcardCodeAnchorQuery extends ParsedQuery {
  kind: QueryKind.WILDCARD_CODE_ANCHOR;
  raw_q: string;
  width: number;
  slots: Array<{ pos: number; kind: string; value?: string }>;
  head_literal?: string;
}

export interface CodeRefMiddleRhymeQuery extends ParsedQuery {
  kind: QueryKind.CODE_REF_MIDDLE_RHYME;
  raw_q: string;
  width: number;
  anchor: string;
  anchor_pos: number;
  leading: string;
  digits: string;
  slots: Array<{ pos: number; kind: string; value?: string }>;
}

export interface TripleRhymeAnchorQuery extends ParsedQuery {
  kind: QueryKind.TRIPLE_RHYME_ANCHOR;
  raw_q: string;
  anchor: string;
  anchor_pos: number;
  width: number;
  leading_slots: string;
  constraint: 'final';
}

/**
 * Relation lookup query (near-synonym or antonym)
 */
export interface RelationLookupQuery extends ParsedQuery {
  kind: QueryKind.RELATION_LOOKUP;
  raw_q: string;
  relation_kind: 'syn' | 'ant';
  word: string;
  code_prefix?: string;
}

/**
 * Unmatched query (invalid syntax)
 */
export interface UnmatchedQuery extends ParsedQuery {
  kind: QueryKind.UNMATCHED;
  raw_q: string;
  hint?: string;
}

/**
 * Query result structure
 */
export interface QueryResult {
  word: string;
  jyutping: string;
  code: string;
  definition?: string;
  score: number;
  /** ponytail: lookup layout row kind — upgrade path: full lookup_layout.ts module */
  resultType?: 'code' | 'jyutping' | 'word';
  heteronym_tags?: string[];
  anchor_dimension?: 'initial' | 'final';
}

/**
 * Search context for query execution
 */
export interface SearchContext {
  q: string | null;
  code?: string;
  char?: string;
  mode: QueryMode;
  limit: number;
  offset: number;
  fallback_0243_mode?: QueryMode;
}

/**
 * Search result with metadata
 */
export interface SearchResult {
  items: QueryResult[];
  total?: number;
  hint?: string;
  cache_path?: string;
  effective_mode?: QueryMode;
}

/** Map lyrics.db row (`char`) to UI-facing QueryResult (`word`). */
function rowToResult(row: Record<string, unknown>): QueryResult {
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

function sortMaskFamilyRows(
  spec: MatchSpec,
  rows: WordRow[],
  db: Database,
  mode: QueryMode,
): WordRow[] {
  if (spec.extra?.dual_phoneme) {
    return rows;
  }
  if (spec.compound_kind) {
    const compoundSpec = compoundSearchSpecFromMatchSpec(spec);
    if (!compoundSpec) {
      return sortWordRows(rows);
    }
    const tiers = searchCompoundTiers(db, compoundSpec);
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
// Query Kind Metadata (from query_kind_registry.py)
// ============================================================================

interface QueryKindMeta {
  route: RouteKind;
  match_spec: boolean;
}

const QUERY_KIND_META: Record<QueryKind, QueryKindMeta> = {
  [QueryKind.RELATION_LOOKUP]: { route: RouteKind.RELATION },
  [QueryKind.COMPOUND_SYN]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_ANT]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_DOUBLED_SYLLABLE]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.HETERONYM_CODE]: { route: RouteKind.HETERONYM },
  [QueryKind.HYBRID_TAIL_EQUALS_ALIAS]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.EQUALS]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PREFIX_WILDCARD_EQUALS]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PARTIAL_RHYME_MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PARTIAL_INITIAL_MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.SERIAL_PHONEME]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PLUS_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.WILDCARD_CODE_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.CODE_REF_MIDDLE_RHYME]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.LITERAL_REF]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.RHYME_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.TRIPLE_RHYME_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.JYUTPING_ANCHOR]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.HYBRID_CODE]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.DIGIT_CODE]: { route: RouteKind.DIGIT },
  [QueryKind.WORD_LOOKUP]: { route: RouteKind.LOOKUP },
  [QueryKind.JYUTPING_FRAGMENT]: { route: RouteKind.LOOKUP },
  [QueryKind.UNMATCHED]: { route: RouteKind.UNMATCHED },
};

const MASK_FAMILY_KINDS: Set<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([_, m]) => m.route === RouteKind.MASK_FAMILY)
    .map(([k]) => k as QueryKind)
);

const MATCH_SPEC_KINDS: Set<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([_, m]) => m.match_spec)
    .map(([k]) => k as QueryKind)
);

function routeKindFor(kind: QueryKind): RouteKind {
  return QUERY_KIND_META[kind]?.route || RouteKind.EMPTY;
}

function usesMatchSpec(kind: QueryKind): boolean {
  return MATCH_SPEC_KINDS.has(kind);
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
  
  return normalized;
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

const FILLWORD_CONNECTIVES = '與和或共同及跟而且並向';
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
export function parseDoubledSyllableSyntax(q: string): CompoundDoubledSyllableQuery | null {
  const m = q.match(/^(\d*)\$\$([\u4e00-\u9fff])?$/);
  if (!m) {
    return null;
  }
  return {
    kind: QueryKind.COMPOUND_DOUBLED_SYLLABLE,
    raw_q: q,
    code_prefix: m[1] || undefined,
    rhyme_char: m[2] || undefined,
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
  if (!q || q.includes('@') || isFramedEqualsQuery(q) || isHybridTailEqualsAlias(q)) {
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

  if (isHybridTailEqualsAlias(q)) {
    return {
      kind: QueryKind.HYBRID_TAIL_EQUALS_ALIAS,
      raw_q: q,
      hybrid_q: hybridQueryFromTailEquals(q),
    } as HybridTailEqualsAliasQuery;
  }

  if (isFramedEqualsQuery(q)) {
    return { kind: QueryKind.EQUALS, raw_q: q } as EqualsQuery;
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

  const hybridCode = parseHybridCodeQuery(q);
  if (hybridCode) {
    return hybridCode;
  }

  return null;
}

/** Port of query_parse.is_relation_syntax_query */
function isRelationSyntaxQuery(q: string): boolean {
  const parsed = normalizeAndParse(q);
  if (parsed.kind === QueryKind.RELATION_LOOKUP) {
    return true;
  }
  return (
    parsed.kind === QueryKind.COMPOUND_SYN ||
    parsed.kind === QueryKind.COMPOUND_ANT ||
    parsed.kind === QueryKind.COMPOUND_DOUBLED_SYLLABLE
  );
}

function resolveFallback0243Mode(fallback?: QueryMode): 'm1' | 'm2' {
  if (fallback === 'm2' || fallback === '02493') {
    return 'm2';
  }
  return 'm1';
}

function modeRedirectHint(mode: 'm1' | 'm2'): string {
  const label = mode === 'm2' ? '02493模式（緊）' : '0243模式（鬆）';
  return `此語法已切換至 ${label} 查詢`;
}

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

/** Port of HYBRID_CODE_RE — must run before looksLikeMaskQuery */
export function parseHybridCodeQuery(q: string): HybridCodeQuery | null {
  const m = q.match(/^(\d+)([\u4e00-\u9fff]+)(\d*)$/);
  if (!m || m[3]) {
    return null;
  }
  return { kind: QueryKind.HYBRID_CODE, raw_q: q };
}

/** Port of plus.parse_at_tail_query — 碼＋@＋尾字（23@就） */
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

const HYBRID_CODE_MATCH_RE = /^(\d+)([\u4e00-\u9fff]+)(\d*)$/;

type HybridMatchSpec = {
  width: number;
  codePrefix: string;
  hybridRefChars: string;
  hybridRefPos: number;
};

function buildHybridMatchSpec(rawQ: string): HybridMatchSpec | null {
  const m = rawQ.match(HYBRID_CODE_MATCH_RE);
  if (!m) {
    return null;
  }
  const numPrefix = m[1]!;
  const refChars = m[2]!;
  const numSuffix = m[3] ?? '';
  const fullCode = numPrefix + numSuffix;
  return {
    width: fullCode.length,
    codePrefix: fullCode,
    hybridRefChars: refChars,
    hybridRefPos: Math.max(0, numPrefix.length - 1),
  };
}

/** Port of filters.build_final_options_at_positions */
function buildFinalOptionsAtPositions(
  db: Database,
  refChars: string,
  startPos: number,
  width: number,
): Array<Set<string> | null> {
  const target: Array<Set<string> | null> = Array.from({ length: width }, () => null);
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos >= 0 && pos < width) {
      const opts = anchorPhonemeOptions(db, refChars[i]!, 'final');
      if (opts.size) {
        target[pos] = opts;
      }
    }
  }
  return target;
}

/** Port of filters.matches_hybrid_ref_chars */
function matchesHybridRefChars(
  wordChar: string,
  wordFinals: string[],
  refChars: string,
  startPos: number,
  targetFinalOptions: Array<Set<string> | null>,
): boolean {
  const width = targetFinalOptions.length;
  if (wordChar.length !== width || wordFinals.length !== width) {
    return false;
  }
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos < 0 || pos >= width) {
      return false;
    }
    if (wordChar[pos] === refChars[i]) {
      continue;
    }
    const options = targetFinalOptions[pos];
    if (options?.size && wordFinals[pos] && options.has(wordFinals[pos]!)) {
      continue;
    }
    return false;
  }
  return true;
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
    ['就=', QueryKind.RHYME_ANCHOR],
    ['?+就=', QueryKind.RHYME_ANCHOR],
    ['?+人=?', QueryKind.TRIPLE_RHYME_ANCHOR],
    ['?30人', QueryKind.WILDCARD_CODE_ANCHOR],
    ['12/12', QueryKind.HETERONYM_CODE],
    ['33~與~你', QueryKind.COMPOUND_SYN],
    ['?=困潦倒', QueryKind.PREFIX_WILDCARD_EQUALS],
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
export function lookupLayoutSelfCheck(): void {
  const rows: WordRow[] = [
    { char: '事業', code: '22', jyutping: 'si6 jip6' },
  ];
  const layout = buildLookupLayout('事業', rows);
  const words = layout.map((r) => r.word);
  const expected = ['22', 'si6 jip6', '事業'];
  if (words.length !== expected.length || words.some((w, i) => w !== expected[i])) {
    throw new Error(`lookupLayoutSelfCheck: got ${words.join(',')}`);
  }
}

/** ponytail: runnable self-check — `npx tsx client/scripts/hybrid-self-check.ts` */
export function hybridLogicSelfCheck(): void {
  const spec = buildHybridMatchSpec('23就');
  if (!spec || spec.width !== 2 || spec.codePrefix !== '23' || spec.hybridRefPos !== 1) {
    throw new Error('hybridLogicSelfCheck: spec parse');
  }
  const target: Array<Set<string> | null> = [null, new Set(['au'])];
  if (!matchesHybridRefChars('成就', ['ing', 'au'], '就', 1, target)) {
    throw new Error('hybridLogicSelfCheck: literal tail match');
  }
  if (matchesHybridRefChars('走先', ['au', 'in'], '就', 1, target)) {
    throw new Error('hybridLogicSelfCheck: rhyme-only reject');
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

/** ponytail: DB + substring infer; upgrade path: lexicon admission union */
function anchorPhonemeOptions(
  db: Database,
  char: string,
  dimension: 'final' | 'initial',
): Set<string> {
  const options = new Set<string>();
  const row = equalsAuthoritativeRow(db, char);
  if (row) {
    const parts = dimension === 'final' ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (parts.length) {
      options.add(parts[0]!);
    }
  }

  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping FROM words WHERE char LIKE ? LIMIT 200',
  );
  stmt.bind([`%${char}%`]);
  while (stmt.step()) {
    const hit = stmt.getAsObject() as WordRow;
    const text = String(hit.char ?? '');
    for (let idx = 0; idx < text.length; idx++) {
      if (text[idx] !== char) {
        continue;
      }
      const parts = dimension === 'final' ? getRhymeFinals(hit) : getWordParts(hit, 'initials');
      if (parts.length > idx && parts[idx]) {
        options.add(parts[idx]!);
      }
    }
  }
  stmt.free();
  return options;
}

// ============================================================================
// Equals Query Support (from query_grammar/equals.py)
// ============================================================================

/**
 * Constants for equals query processing
 */
export const CODE_TAIL_MIDDLE = '\u2215'; // Division slash (∕)

/**
 * Regex for hybrid tail equals alias (e.g., 23就=)
 */
const HYBRID_TAIL_EQUALS_RE = /^(\d+)([\u4e00-\u9fff])=$/;

/**
 * Equals query interface
 */
export interface EqualsQuery extends ParsedQuery {
  kind: QueryKind.EQUALS;
  raw_q: string;
}

/**
 * Hybrid tail equals alias query interface
 */
export interface HybridTailEqualsAliasQuery extends ParsedQuery {
  kind: QueryKind.HYBRID_TAIL_EQUALS_ALIAS;
  raw_q: string;
  hybrid_q: string;
}

/**
 * Check if query is a hybrid tail equals alias (e.g., 23就=)
 */
export function isHybridTailEqualsAlias(q: string): boolean {
  return HYBRID_TAIL_EQUALS_RE.test(q);
}

/**
 * Convert hybrid tail equals query to hybrid query
 * e.g., "23就=" -> "23就"
 */
export function hybridQueryFromTailEquals(q: string): string {
  return q.slice(0, -1);
}

/**
 * Check if query is a framed equals query
 * e.g., "香港=", "2=我3", "=香", "就="
 */
export function isFramedEqualsQuery(q: string): boolean {
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes('@') || isHybridTailEqualsAlias(q)) {
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
const CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT = 
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
  
  const code = spec.code_prefix || '';
  const literal = span.ref_literal;
  
  if (!code || code.length !== literal.length) {
    return null;
  }
  
  // Check if the literal exists in the database
  const sql = 'SELECT COUNT(*) as count FROM words WHERE char = ?';
  const stmt = db.prepare(sql);
  stmt.bind([literal]);
  const result = stmt.step() ? stmt.getAsObject() : { count: 0 };
  stmt.free();
  
  if (result.count === 0) {
    return null;
  }
  
  // Literal exists but no results - generate hint
  return CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT
    .replace('{literal}', literal)
    .replace('{code}', code);
}

// ============================================================================
// Query Execution
// ============================================================================

/**
 * Execute a search query using the SQL.js database
 */
export async function executeSearch(ctx: SearchContext): Promise<SearchResult> {
  // Ensure database is initialized
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  
  const db = getDatabase();
  
  // Parse the query
  if (!ctx.q) {
    // Empty query - return all words with filters
    return executeListFilter(db, ctx);
  }
  
  const parsed = normalizeAndParse(ctx.q);
  return await dispatch(parsed, { ...ctx, db });
}

/**
 * Execute list filter (when query is empty)
 */
function executeListFilter(db: Database, ctx: SearchContext): SearchResult {
  const { limit, offset } = ctx;
  const sql = `SELECT char, jyutping, code FROM words ORDER BY char LIMIT ? OFFSET ?`;
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([limit, offset]);
  
  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();
  
  return { items: results };
}

/**
 * Dispatch query based on parsed type
 */
async function dispatch(parsed: ParsedQuery, ctx: SearchContext & { db: Database }): Promise<SearchResult> {
  const routeKind = routeKindFor(parsed.kind);
  const { db, mode, limit, offset } = ctx;
  
  switch (routeKind) {
    case RouteKind.DIGIT:
      if (parsed.kind === QueryKind.DIGIT_CODE) {
        return executeDigitCodeQuery(parsed as DigitCodeQuery, db, mode, limit, offset);
      }
      break;
    
    case RouteKind.LOOKUP:
      if (parsed.kind === QueryKind.WORD_LOOKUP) {
        return executeWordLookup(parsed as WordLookupQuery, db, mode, limit, offset);
      }
      if (parsed.kind === QueryKind.JYUTPING_FRAGMENT) {
        return executeJyutpingFragment(parsed as JyutpingFragmentQuery, db, limit, offset);
      }
      break;
    
    case RouteKind.MASK_FAMILY:
      return executeMaskFamilySearchResult(parsed, db, mode, limit, offset, ctx.code);
    
    case RouteKind.RELATION:
      if (parsed.kind === QueryKind.RELATION_LOOKUP) {
        return executeRelationLookup(parsed as RelationLookupQuery, db, mode, limit, offset);
      }
      break;

    case RouteKind.HETERONYM:
      if (parsed.kind === QueryKind.HETERONYM_CODE) {
        const h = parsed as HeteronymCodeQuery;
        const items = executeHeteronymCodeSearch(h, db, mode, limit, offset);
        return { items };
      }
      return { items: [] };
    
    case RouteKind.UNMATCHED:
      if (parsed.kind === QueryKind.UNMATCHED) {
        const unmatched = parsed as UnmatchedQuery;
        return { items: [], hint: unmatched.hint };
      }
      break;
  }
  
  return { items: [] };
}

function normalizeSearchMode(mode: QueryMode): 'm1' | 'm2' {
  if (mode === 'm2' || mode === '02493') {
    return 'm2';
  }
  return 'm1';
}

/**
 * Execute digit code query (pure digits only — P0 scope A)
 */
function executeDigitCodeQuery(
  parsed: DigitCodeQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  const q = parsed.raw_q;
  const searchMode = normalizeSearchMode(mode);
  const variants = getCodeVariants(q, searchMode);
  const placeholders = variants.map(() => '?').join(', ');
  const len = q.length;

  const sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE code IN (${placeholders})
      AND (
        length = ?
        OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
    ORDER BY char
    LIMIT ? OFFSET ?
  `;

  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];

  stmt.bind([...variants, len, len, limit, offset]);

  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();

  return { items: results };
}

/** Port of word_serializer.deduplicate_words */
function deduplicateWordRows(rows: WordRow[]): WordRow[] {
  const seen = new Set<string>();
  const out: WordRow[] = [];
  for (const row of rows) {
    const c = String(row.char ?? '');
    if (!c || seen.has(c)) {
      continue;
    }
    seen.add(c);
    out.push(row);
  }
  return out;
}

function getWordSortCode(row: WordRow): string {
  const code = String(row.code ?? '').trim();
  if (code) {
    return code;
  }
  // ponytail: no jyutping→0243 derive yet
  return '';
}

/** Port of lookup_layout._collect_codes_and_jyuts */
function collectCodesAndJyuts(rows: WordRow[]): {
  codes: string[];
  codeToJyuts: Map<string, string[]>;
} {
  const codes: string[] = [];
  const seenCodes = new Set<string>();
  const codeToJyuts = new Map<string, string[]>();
  for (const row of rows) {
    const c = getWordSortCode(row);
    if (c && /^\d+$/.test(c) && !seenCodes.has(c)) {
      seenCodes.add(c);
      codes.push(c);
    }
    const j = String(row.jyutping ?? '').trim();
    if (c && j) {
      const list = codeToJyuts.get(c) ?? [];
      if (!list.includes(j)) {
        list.push(j);
      }
      codeToJyuts.set(c, list);
    }
  }
  codes.sort((a, b) => Number(a) - Number(b));
  return { codes, codeToJyuts };
}

/** Port of lookup_layout code/jyutping headers + exact word rows (rhyme sections: later) */
function buildLookupLayout(_q: string, exactMatches: WordRow[]): QueryResult[] {
  if (!exactMatches.length) {
    return [];
  }
  const results: QueryResult[] = [];
  const seenWords = new Set<string>();
  const { codes, codeToJyuts } = collectCodesAndJyuts(exactMatches);

  for (const code of codes) {
    results.push({ word: code, code, jyutping: '', score: 0, resultType: 'code' });
  }
  const seenJyuts = new Set<string>();
  for (const code of codes) {
    for (const jy of codeToJyuts.get(code) ?? []) {
      const j = jy.trim();
      if (!j || seenJyuts.has(j)) {
        continue;
      }
      seenJyuts.add(j);
      results.push({ word: j, code: '', jyutping: j, score: 0, resultType: 'jyutping' });
    }
  }
  for (const row of deduplicateWordRows(exactMatches)) {
    const char = String(row.char ?? '');
    if (!char || seenWords.has(char)) {
      continue;
    }
    seenWords.add(char);
    results.push({ ...rowToResult(row), resultType: 'word' });
  }
  return results;
}

/**
 * Execute word lookup query
 */
function executeWordLookup(
  parsed: WordLookupQuery,
  db: Database,
  _mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const stmt = db.prepare(
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
  );
  stmt.bind([parsed.raw_q]);

  const matches: WordRow[] = [];
  while (stmt.step()) {
    matches.push(stmt.getAsObject() as WordRow);
  }
  stmt.free();

  const built = buildLookupLayout(parsed.raw_q, deduplicateWordRows(matches));
  return { items: built.slice(offset, offset + limit) };
}

/**
 * Execute jyutping fragment query
 */
function executeJyutpingFragment(
  parsed: JyutpingFragmentQuery,
  db: Database,
  limit: number,
  offset: number
): SearchResult {
  const sql = `
    SELECT char, jyutping, code 
    FROM words 
    WHERE jyutping LIKE ?
    ORDER BY char 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([`%${parsed.raw_q}%`, limit, offset]);
  
  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();
  
  return { items: results };
}

type WordRow = Record<string, unknown>;

function loadJsonList(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(String);
  }
  if (typeof raw === 'string' && raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  return [];
}

function getWordParts(row: WordRow, field: 'initials' | 'finals'): string[] {
  return loadJsonList(row[field]);
}

function getRhymeFinals(row: WordRow): string[] {
  const fromCol = getWordParts(row, 'finals');
  if (fromCol.length) {
    return fromCol;
  }
  const jyut = String(row.jyutping ?? '');
  return jyut ? rhymeFinalsFromJyutping(jyut) : [];
}

function equalsAuthoritativeRow(db: Database, literal: string): WordRow | null {
  const stmt = db.prepare(
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
  );
  stmt.bind([literal]);
  const row = stmt.step() ? (stmt.getAsObject() as WordRow) : null;
  stmt.free();
  return row;
}

/** MF-6: port of query_dispatch._mask_family_search_result */
async function executeMaskFamilySearchResult(
  parsed: ParsedQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
  code?: string,
): Promise<SearchResult> {
  const spec = normalizeToMatchSpec(parsed);
  if (!spec) {
    return { items: [] };
  }
  const searchMode = normalizeSearchMode(mode);
  const rows = executeMatchSpec(spec, {
    db,
    mode: searchMode,
    limit,
    offset,
    code: code ?? null,
  });
  const ordered = sortMaskFamilyRows(spec, rows, db, mode);
  const items = spec.extra?.dual_phoneme
    ? ordered.map((row) => rowToResult(row))
    : sortQueryResults(ordered.map((row) => rowToResult(row)));
  let hint: string | undefined;
  if (!items.length && getEqualsSpan(spec)) {
    const emptyHint = await codePrefixedWholeWordEqualsEmptyHint(spec, db);
    if (emptyHint) {
      hint = emptyHint;
    }
  }
  return { items, hint };
}

function executeRelationLookup(
  parsed: RelationLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const seed = parsed.word.trim();
  if (!seed) {
    return { items: [] };
  }

  const rows = relationLookupItems(
    db,
    seed,
    parsed.relation_kind,
    mode,
    parsed.code_prefix,
    limit,
    offset,
  );

  return {
    items: rows.map((r) => ({
      word: r.char,
      jyutping: r.jyutping,
      code: r.code,
      score: r.score ?? 0,
    })),
  };
}

// ============================================================================
// Query Engine Class (from query_dispatch.py)
// ============================================================================

/**
 * Main Query Engine class
 * Provides high-level search interface
 */
export class QueryEngine {
  private db: Database | null = null;
  
  /**
   * Execute a search query
   */
  async execute(ctx: SearchContext): Promise<SearchResult> {
    // Initialize database if needed
    if (!isDatabaseInitialized()) {
      await initializeDatabase();
    }
    this.db = getDatabase();
    
    // If no database, return empty
    if (!this.db) {
      return { items: [], hint: '資料庫初始化失敗' };
    }
    
    // Add database to context
    const dbCtx = { ...ctx, db: this.db };
    
    // Handle empty query
    if (!ctx.q) {
      return executeListFilter(this.db, ctx);
    }
    
    // Normalize and parse
    const q = normalizeQuery(ctx.q);
    
    // Handle syn mode
    if (ctx.mode === 'syn') {
      return this.dispatchSynMode({ ...ctx, q }, dbCtx);
    }
    
    // Parse and dispatch
    const parsed = normalizeAndParse(ctx.q);
    return await dispatch(parsed, dbCtx);
  }
  
  /**
   * Dispatch synonym mode queries (port of query_mode_dispatch.dispatch_syn_mode)
   */
  private async dispatchSynMode(ctx: SearchContext & { q: string }, dbCtx: SearchContext & { db: Database }): Promise<SearchResult> {
    if (isRelationSyntaxQuery(ctx.q)) {
      const effective = resolveFallback0243Mode(ctx.fallback_0243_mode);
      const parsed = normalizeAndParse(ctx.q);
      const result = await dispatch(parsed, { ...dbCtx, mode: effective, offset: 0 });
      return {
        items: result.items,
        total: result.total,
        hint: modeRedirectHint(effective),
        effective_mode: effective,
        cache_path: result.cache_path,
      };
    }
    // ponytail: syn_mode_page (pool browse) — upgrade: RelationSyntaxExecutor.syn_mode_page
    return { items: [] };
  }
}

// Singleton engine instance
export const queryEngine = new QueryEngine();

// ============================================================================
// Public API
// ============================================================================

/**
 * Main search function - public entry point
 */
export async function searchWords(
  q: string | null = null,
  code?: string,
  char?: string,
  mode: QueryMode = '0243',
  limit: number = 100,
  offset: number = 0,
): Promise<QueryResult[]> {
  const result = await queryEngine.execute({
    q: q || undefined,
    code,
    char,
    mode,
    limit,
    offset,
  });
  return result.items;
}

// Export all types and functions
export type {
  QueryMode,
  QueryKind,
  RouteKind,
  ParsedQuery,
  QueryResult,
  SearchContext,
  SearchResult,
  DigitCodeQuery,
  WordLookupQuery,
  JyutpingFragmentQuery,
  MaskQuery,
  RelationLookupQuery,
  UnmatchedQuery,
  MatchSpec,
  EqualsSpan,
  EqualsDimension,
  SlotConstraint,
  ConstraintKind,
  CompoundKind,
  CandidateSource,
  MaskFamilySearchResult,
};
export {
  attachEqualsSpan,
  createMatchSpec,
  getEqualsSpan,
  positionMatchSpecSelfCheck,
} from './position-match/spec.ts';
export {
  buildEqualsMatchSpec,
} from './position-match/equals-spec.ts';
export {
  buildMaskFromSlots,
  isWildcardChar,
  parseMaskQuery,
} from './position-match/mask-grammar.ts';
export {
  buildJyutpingDualMatchSpecs,
  buildMatchSpecForParsed,
  MATCH_SPEC_BUILDERS,
  normalizeToMatchSpec,
  rewriteMaskFamilyAliases,
} from './position-match/match-spec-registry.ts';
export {
  executeMatchSpec,
} from './position-match/engine.ts';
export {
  getCandidatesForLength,
  LengthCodeCandidateSource,
  positionMatchSourcesSelfCheck,
  wordMatchesWidth,
} from './position-match/sources.ts';
