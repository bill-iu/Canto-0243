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
import { sortQueryResults, sortWordRows } from './ranking.ts';
import {
  executeCompoundSearch,
  type CompoundSearchSpec,
} from './compound.ts';
import { executeHeteronymCodeSearch } from './heteronym.ts';
import { relationLookupItems } from './relation-pool.ts';
import {
  matchesJyutpingAnchorAtPosition,
  parseJyutpingAnchorQuery as parseJyutpingAnchorFields,
} from './jyutping-anchor.ts';
import { rhymeFinalsFromJyutping } from './jyutping-codec.ts';

// ============================================================================
// Query Types and Constants
// ============================================================================

/**
 * Query modes supported by the engine
 */
export type QueryMode = 'm1' | 'm2' | '0243' | '02493' | 'syn';

/**
 * Query kind enumeration - maps to Python QueryKind
 */
export enum QueryKind {
  RELATION_LOOKUP = 'relation_lookup',
  COMPOUND_ANT = 'compound_ant',
  COMPOUND_SYN = 'compound_syn',
  COMPOUND_DOUBLED_SYLLABLE = 'compound_doubled_syllable',
  HETERONYM_CODE = 'heteronym_code',
  HYBRID_TAIL_EQUALS_ALIAS = 'hybrid_tail_equals_alias',
  EQUALS = 'equals',
  PLUS_ANCHOR = 'plus_anchor',
  WILDCARD_CODE_ANCHOR = 'wildcard_code_anchor',
  CODE_REF_MIDDLE_RHYME = 'code_ref_middle_rhyme',
  SERIAL_PHONEME = 'serial_phoneme',
  PREFIX_WILDCARD_EQUALS = 'prefix_wildcard_equals',
  PARTIAL_RHYME_MASK = 'partial_rhyme_mask',
  PARTIAL_INITIAL_MASK = 'partial_initial_mask',
  LITERAL_REF = 'literal_ref',
  RHYME_ANCHOR = 'rhyme_anchor',
  TRIPLE_RHYME_ANCHOR = 'triple_rhyme_anchor',
  JYUTPING_ANCHOR = 'jyutping_anchor',
  HYBRID_CODE = 'hybrid_code',
  MASK = 'mask',
  DIGIT_CODE = 'digit_code',
  WORD_LOOKUP = 'word_lookup',
  JYUTPING_FRAGMENT = 'jyutping_fragment',
  UNMATCHED = 'unmatched',
}

/**
 * Route kind for query dispatch
 */
export enum RouteKind {
  DIGIT = 'digit',
  MASK_FAMILY = 'mask_family',
  RELATION = 'relation',
  HETERONYM = 'heteronym',
  LOOKUP = 'lookup',
  UNMATCHED = 'unmatched',
  EMPTY = 'empty',
}

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
  return {
    word: String(row.char ?? ''),
    jyutping: String(row.jyutping ?? ''),
    code: String(row.code ?? ''),
    score: 0,
  };
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
  [QueryKind.HYBRID_TAIL_EQUALS_ALIAS]: { route: RouteKind.MASK_FAMILY },
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

/** ponytail: compound tiers — connective width-3 via compound_connect port */
function buildCompoundSearchSpec(
  parsed: CompoundSynQuery | CompoundAntQuery | CompoundDoubledSyllableQuery,
): CompoundSearchSpec | null {
  if (parsed.kind === QueryKind.COMPOUND_DOUBLED_SYLLABLE) {
    return {
      compound_kind: 'doubled_syllable',
      width: 2,
      code_prefix: parsed.code_prefix,
      rhyme_char: parsed.rhyme_char,
    };
  }
  if (parsed.kind === QueryKind.COMPOUND_SYN) {
    const connect = parsed.raw_q.match(
      /^(\d*)~([與和或共同及跟而且並向])~([\u4e00-\u9fff])?$/,
    );
    if (connect) {
      return {
        compound_kind: 'syn',
        width: 3,
        code_prefix: connect[1] || undefined,
        connective: connect[2],
        rhyme_char: connect[3] || undefined,
      };
    }
    return {
      compound_kind: 'syn',
      width: 2,
      code_prefix: parsed.code_prefix,
      rhyme_char: parsed.rhyme_char,
    };
  }
  if (parsed.kind === QueryKind.COMPOUND_ANT) {
    const connect = parsed.raw_q.match(
      /^(\d*)!([與和或共同及跟而且並向])!([\u4e00-\u9fff])?$/,
    );
    if (connect) {
      return {
        compound_kind: 'ant',
        width: 3,
        code_prefix: connect[1] || undefined,
        connective: connect[2],
        rhyme_char: connect[3] || undefined,
      };
    }
    return {
      compound_kind: 'ant',
      width: 2,
      code_prefix: parsed.code_prefix,
      rhyme_char: parsed.rhyme_char,
    };
  }
  return null;
}

function executeCompoundQuery(
  parsed: CompoundSynQuery | CompoundAntQuery | CompoundDoubledSyllableQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const spec = buildCompoundSearchSpec(parsed);
  if (!spec) {
    return { items: [] };
  }
  const items = executeCompoundSearch(db, spec, mode, limit, offset);
  return { items };
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

/** Port of query_grammar/mask.parse_mask_query */
function parseMaskQuery(
  mask: string,
): { width: number; requiredCodes: Array<string | null>; literalPositions: Array<[number, string]> } {
  const requiredCodes: Array<string | null> = Array(mask.length).fill(null);
  const literalPositions: Array<[number, string]> = [];
  for (let idx = 0; idx < mask.length; idx++) {
    const ch = mask[idx]!;
    if (isWildcardChar(ch)) {
      continue;
    }
    if (/\d/.test(ch)) {
      requiredCodes[idx] = ch;
      continue;
    }
    literalPositions.push([idx, ch]);
  }
  return { width: mask.length, requiredCodes, literalPositions };
}

function matchesCodePositions(
  codeStr: string,
  requiredCodes: Array<string | null>,
  mode: 'm1' | 'm2',
): boolean {
  if (codeStr.length !== requiredCodes.length) {
    return false;
  }
  for (let idx = 0; idx < requiredCodes.length; idx++) {
    const req = requiredCodes[idx];
    if (!req) {
      continue;
    }
    const variants = new Set(getCodeVariants(req, mode));
    if (!variants.has(codeStr[idx]!)) {
      return false;
    }
  }
  return true;
}

function matchesMaskLiteralPositions(
  wordChar: string,
  literalPositions: Array<[number, string]>,
): boolean {
  for (const [idx, ch] of literalPositions) {
    if (wordChar[idx] !== ch) {
      return false;
    }
  }
  return true;
}

function executeMaskQuery(
  parsed: MaskQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const { width, requiredCodes, literalPositions } = parseMaskQuery(parsed.raw_q);
  const searchMode = normalizeSearchMode(mode);

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);

  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const charText = String(row.char ?? '');
    if (!wordMatchesWidth(row, width) || charText.length !== width) {
      continue;
    }
    if (!matchesMaskLiteralPositions(charText, literalPositions)) {
      continue;
    }
    const code = String(row.code ?? '');
    if (!matchesCodePositions(code, requiredCodes, searchMode)) {
      continue;
    }
    matched.push(rowToResult(row));
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

/** Port of plus_anchor MatchSpec — code_digit slots + literal/final/initial anchor */
function executePlusAnchorQuery(
  parsed: PlusAnchorQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const width = parsed.width;
  const requiredCodes: Array<string | null> = Array(width).fill(null);
  for (const [pos, digit] of parsed.code_slots) {
    requiredCodes[pos] = digit;
  }
  const searchMode = normalizeSearchMode(mode);

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);

  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const charText = String(row.char ?? '');
    if (!wordMatchesWidth(row, width) || charText.length !== width) {
      continue;
    }
    if (parsed.constraint === 'literal' && charText[parsed.anchor_pos] !== parsed.anchor) {
      continue;
    }
    if (
      parsed.constraint === 'final' &&
      !matchesPhonemeAtPosition(row, parsed.anchor_pos, parsed.anchor, 'final', db)
    ) {
      continue;
    }
    if (
      parsed.constraint === 'initial' &&
      !matchesPhonemeAtPosition(row, parsed.anchor_pos, parsed.anchor, 'initial', db)
    ) {
      continue;
    }
    const code = String(row.code ?? '');
    if (!matchesCodePositions(code, requiredCodes, searchMode)) {
      continue;
    }
    matched.push(rowToResult(row));
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
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

/** Port of filters.filter_hybrid_ref_candidates */
function filterHybridRefCandidates(
  candidates: WordRow[],
  spec: HybridMatchSpec,
  mode: 'm1' | 'm2',
  db: Database,
): WordRow[] {
  const targetFinalOptions = buildFinalOptionsAtPositions(
    db,
    spec.hybridRefChars,
    spec.hybridRefPos,
    spec.width,
  );
  const allowedCodes = spec.codePrefix
    ? new Set(getCodeVariants(spec.codePrefix, mode))
    : null;

  const filtered: WordRow[] = [];
  for (const word of candidates) {
    const wordCode = String(word.code ?? '');
    if (allowedCodes && !allowedCodes.has(wordCode)) {
      continue;
    }
    const wordChar = String(word.char ?? '');
    const wordFinals = getRhymeFinals(word);
    if (
      matchesHybridRefChars(
        wordChar,
        wordFinals,
        spec.hybridRefChars,
        spec.hybridRefPos,
        targetFinalOptions,
      )
    ) {
      filtered.push(word);
    }
  }
  return filtered;
}

/** Port of filter_hybrid_ref_candidates + position_match engine width bucket */
function executeHybridCodeQuery(
  parsed: HybridCodeQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const spec = buildHybridMatchSpec(parsed.raw_q);
  if (!spec) {
    return { items: [] };
  }
  const searchMode = normalizeSearchMode(mode);

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([spec.width, spec.width]);

  const candidates: WordRow[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const charText = String(row.char ?? '');
    if (!wordMatchesWidth(row, spec.width) || charText.length !== spec.width) {
      continue;
    }
    candidates.push(row);
  }
  stmt.free();

  const matched = filterHybridRefCandidates(candidates, spec, searchMode, db);
  const sorted = sortWordRows(matched);
  return { items: sorted.slice(offset, offset + limit).map((r) => rowToResult(r)) };
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

/** Port of literal_ref MatchSpec execution — code per position + tail literal */
function executeLiteralRefQuery(
  parsed: LiteralRefQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const { code_digits, literal_char, width } = parsed;
  const searchMode = normalizeSearchMode(mode);
  const requiredCodes = [...code_digits];

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);

  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const charText = String(row.char ?? '');
    if (!wordMatchesWidth(row, width) || charText.length !== width) {
      continue;
    }
    if (charText[width - 1] !== literal_char) {
      continue;
    }
    const code = String(row.code ?? '');
    if (!matchesCodePositions(code, requiredCodes, searchMode)) {
      continue;
    }
    matched.push(rowToResult(row));
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

const WILDCARD_CHARS = new Set(['_', '?', '%']);
const SLOT_CHAR_RE = /[0-9_?%]/;

function isWildcardChar(ch: string): boolean {
  return ch.length === 1 && WILDCARD_CHARS.has(ch);
}

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

/** Port of query_grammar/mask.build_mask_from_slots */
function buildMaskFromSlots(slots: string, width: number, anchorPos: number): string {
  const chars = Array(width).fill('?');
  if (anchorPos === 0) {
    for (let i = 0; i < slots.length; i++) {
      chars[i + 1] = slots[i]!;
    }
  } else {
    for (let i = 0; i < slots.length; i++) {
      chars[i] = slots[i]!;
    }
  }
  return chars.join('');
}

function matchesMaskLiteralChars(wordChar: string, mask: string): boolean {
  if (wordChar.length !== mask.length) {
    return false;
  }
  for (let idx = 0; idx < mask.length; idx++) {
    const ch = mask[idx]!;
    if (isWildcardChar(ch) || /\d/.test(ch)) {
      continue;
    }
    if (wordChar[idx] !== ch) {
      return false;
    }
  }
  return true;
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

function contextualFinalOptionsAtPosition(
  db: Database,
  width: number,
  pos: number,
  anchorChar: string,
): Set<string> {
  const options = new Set<string>();
  const stmt = db.prepare(`
    SELECT char, initials, finals, jyutping, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const text = String(row.char ?? '');
    if (text.length !== width || text[pos] !== anchorChar) {
      continue;
    }
    const finals = getRhymeFinals(row);
    if (finals.length > pos && finals[pos]) {
      options.add(finals[pos]!);
    }
  }
  stmt.free();
  for (const opt of anchorPhonemeOptions(db, anchorChar, 'final')) {
    options.add(opt);
  }
  return options;
}

function contextualInitialOptionsAtPosition(
  db: Database,
  width: number,
  pos: number,
  anchorChar: string,
): Set<string> {
  const options = new Set<string>();
  const stmt = db.prepare(`
    SELECT char, initials, finals, jyutping, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const text = String(row.char ?? '');
    if (text.length !== width || text[pos] !== anchorChar) {
      continue;
    }
    const initials = getWordParts(row, 'initials');
    if (initials.length > pos && initials[pos]) {
      options.add(initials[pos]!);
    }
  }
  stmt.free();
  for (const opt of anchorPhonemeOptions(db, anchorChar, 'initial')) {
    options.add(opt);
  }
  return options;
}

function wordPassesPartialRhymeMask(
  word: WordRow,
  parsed: PartialRhymeMaskQuery,
  slotOptions: Map<string, Set<string>>,
  width: number,
): boolean {
  const text = String(word.char ?? '');
  if (text.length !== width) {
    return false;
  }
  const finals = getRhymeFinals(word);
  if (!finals.length) {
    return false;
  }
  for (const [pos, anchor] of parsed.anchors) {
    const options = slotOptions.get(`${pos}:${anchor}`);
    if (!options?.size || pos >= finals.length || !options.has(finals[pos]!)) {
      return false;
    }
  }
  return true;
}

function executePartialRhymeMaskQuery(
  parsed: PartialRhymeMaskQuery,
  db: Database,
  limit: number,
  offset: number,
): SearchResult {
  const width = parsed.width;
  const slotOptions = new Map<string, Set<string>>();
  for (const [pos, anchor] of parsed.anchors) {
    const key = `${pos}:${anchor}`;
    if (!slotOptions.has(key)) {
      slotOptions.set(key, contextualFinalOptionsAtPosition(db, width, pos, anchor));
    }
  }

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);
  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    if (wordPassesPartialRhymeMask(word, parsed, slotOptions, width)) {
      matched.push(rowToResult(word));
    }
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

function wordPassesPartialInitialMask(
  word: WordRow,
  parsed: PartialInitialMaskQuery,
  slotOptions: Map<string, Set<string>>,
  width: number,
): boolean {
  const text = String(word.char ?? '');
  if (text.length !== width) {
    return false;
  }
  const initials = getWordParts(word, 'initials');
  if (!initials.length) {
    return false;
  }
  for (const [pos, ch] of parsed.pattern.split('').entries()) {
    if (ch === '?') {
      continue;
    }
    if (text[pos] !== ch) {
      return false;
    }
  }
  for (const [pos, anchor] of parsed.anchors) {
    const options = slotOptions.get(`${pos}:${anchor}`);
    if (!options?.size || pos >= initials.length || !options.has(initials[pos]!)) {
      return false;
    }
  }
  return true;
}

function executePartialInitialMaskQuery(
  parsed: PartialInitialMaskQuery,
  db: Database,
  limit: number,
  offset: number,
): SearchResult {
  const width = parsed.width;
  const slotOptions = new Map<string, Set<string>>();
  for (const [pos, anchor] of parsed.anchors) {
    const key = `${pos}:${anchor}`;
    if (!slotOptions.has(key)) {
      slotOptions.set(key, contextualInitialOptionsAtPosition(db, width, pos, anchor));
    }
  }

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);
  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    if (wordPassesPartialInitialMask(word, parsed, slotOptions, width)) {
      matched.push(rowToResult(word));
    }
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

function executeSerialPhonemeQuery(
  parsed: SerialPhonemeAnchorQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const { width, constraint, code_slots, anchors } = parsed;
  const searchMode = normalizeSearchMode(mode);
  const requiredCodes: Array<string | null> = Array(width).fill(null);
  for (const [pos, digit] of code_slots) {
    requiredCodes[pos] = digit;
  }

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);

  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    const charText = String(word.char ?? '');
    if (!wordMatchesWidth(word, width) || charText.length !== width) {
      continue;
    }
    const code = String(word.code ?? '');
    if (!matchesCodePositions(code, requiredCodes, searchMode)) {
      continue;
    }
    let ok = true;
    for (const [pos, anchor] of anchors) {
      if (!matchesPhonemeAtPosition(word, pos, anchor, constraint === 'final' ? 'final' : 'initial', db)) {
        ok = false;
        break;
      }
    }
    if (ok) {
      matched.push(rowToResult(word));
    }
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

function executeDualPhonemeJyutpingQuery(
  parsed: JyutpingAnchorQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const initialLetter = /m/i.test(parsed.raw_q) ? 'm' : parsed.anchor_value;
  const initialParsed: JyutpingAnchorQuery = {
    ...parsed,
    anchor_kind: 'initial_letters',
    anchor_value: initialLetter,
    dual_phoneme: false,
  };
  const finalParsed: JyutpingAnchorQuery = {
    ...parsed,
    anchor_kind: 'rhyme_letters',
    anchor_value: parsed.anchor_value === 'm' ? 'ng' : parsed.anchor_value,
    dual_phoneme: false,
  };
  const initial = executeJyutpingAnchorQuery(initialParsed, db, mode, limit + offset + 500, 0);
  const final = executeJyutpingAnchorQuery(finalParsed, db, mode, limit + offset + 500, 0);
  const tagged: QueryResult[] = [
    ...initial.items.map((r) => ({ ...r, anchor_dimension: 'initial' as const })),
    ...final.items.map((r) => ({ ...r, anchor_dimension: 'final' as const })),
  ];
  return { items: tagged.slice(offset, offset + limit) };
}

function executeJyutpingAnchorQuery(
  parsed: JyutpingAnchorQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  if (parsed.dual_phoneme) {
    return executeDualPhonemeJyutpingQuery(parsed, db, mode, limit, offset);
  }

  const width = parsed.width;
  const searchMode = normalizeSearchMode(mode);
  const requiredCodes: Array<string | null> = Array(width).fill(null);
  if (parsed.code_slots?.length) {
    for (const [pos, digit] of parsed.code_slots) {
      requiredCodes[pos] = digit;
    }
  } else if (parsed.code_prefix) {
    for (let i = 0; i < Math.min(parsed.code_prefix.length, width); i++) {
      requiredCodes[i] = parsed.code_prefix[i]!;
    }
  }

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);

  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    const charText = String(word.char ?? '');
    if (!wordMatchesWidth(word, width) || charText.length !== width) {
      continue;
    }
    const code = String(word.code ?? '');
    const hasCodeFilter = Boolean(parsed.code_slots?.length || parsed.code_prefix);
    if (hasCodeFilter && !matchesCodePositions(code, requiredCodes, searchMode)) {
      continue;
    }
    if (
      !matchesJyutpingAnchorAtPosition(
        word,
        parsed.anchor_pos,
        parsed.anchor_kind,
        parsed.anchor_value,
      )
    ) {
      continue;
    }
    matched.push(rowToResult(word));
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

function matchesPhonemeAtPosition(
  word: WordRow,
  pos: number,
  anchor: string,
  constraint: 'final' | 'initial',
  db: Database,
): boolean {
  const options = anchorPhonemeOptions(db, anchor, constraint);
  const parts = constraint === 'final' ? getRhymeFinals(word) : getWordParts(word, 'initials');
  if (!options.size || pos >= parts.length) {
    return false;
  }
  return options.has(parts[pos]!);
}

function executeRhymeAnchorQuery(
  parsed: RhymeAnchorQuery,
  db: Database,
  limit: number,
  offset: number,
): SearchResult {
  const mask = buildMaskFromSlots(parsed.slots, parsed.width, parsed.anchor_pos);
  const width = parsed.width;

  const stmt = db.prepare(`
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 2000
  `);
  stmt.bind([width, width]);
  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    const charText = String(word.char ?? '');
    if (!wordMatchesWidth(word, width)) {
      continue;
    }
    if (!matchesMaskLiteralChars(charText, mask)) {
      continue;
    }
    if (
      !matchesPhonemeAtPosition(
        word,
        parsed.anchor_pos,
        parsed.anchor,
        parsed.constraint,
        db,
      )
    ) {
      continue;
    }
    matched.push(rowToResult(word));
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

// ============================================================================
// Match Specification (from position_match/spec.py)
// ============================================================================

/**
 * Position match specification
 */
export interface MatchSpec {
  width: number; // Number of syllables/characters
  code_prefix?: string;
  equals_span?: EqualsSpan; // For equals queries
  // Additional spec properties would be added here
  // This is a simplified version
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
 * Dimension type for equals span
 */
export type EqualsDimension = 'initial' | 'final' | 'rhyme' | 'phone';

/**
 * Equals span specification for position matching
 */
export interface EqualsSpan {
  ref_literal: string;
  start_pos: number;
  dimension: EqualsDimension;
  phoneme_anchor_only: boolean;
  whole_word: boolean;
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
 * Build MatchSpec for equals query
 * Converts query string to MatchSpec for position matching
 */
export function buildEqualsMatchSpec(q: string): (MatchSpec & { equals_span: EqualsSpan }) | null {
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)?(=)?(\d*)$/);
  if (!match) {
    return null;
  }
  
  const target_str = match[3] || '';
  if (!target_str) {
    return null;
  }
  
  const left_code = match[1] || '';
  const right_code = match[5] || '';
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  const target_length = target_str.length;
  const expected_length = left_code.length + right_code.length || target_length;
  const start_pos = Math.max(0, left_code.length - target_length);
  const full_code = left_code + right_code;
  
  const span: EqualsSpan = {
    ref_literal: target_str,
    start_pos: start_pos,
    dimension: right_equal ? 'final' : 'initial',
    phoneme_anchor_only: Boolean(left_code && (right_code || inner_equal)),
    whole_word: start_pos === 0 && target_length === expected_length,
  };
  
  return {
    width: expected_length,
    code_prefix: full_code || undefined,
    equals_span: span,
  };
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
  spec: MatchSpec & { equals_span?: EqualsSpan },
  db: Database
): Promise<string | null> {
  const span = spec.equals_span;
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
      if (
        parsed.kind === QueryKind.COMPOUND_SYN ||
        parsed.kind === QueryKind.COMPOUND_ANT ||
        parsed.kind === QueryKind.COMPOUND_DOUBLED_SYLLABLE
      ) {
        return executeCompoundQuery(
          parsed as CompoundSynQuery | CompoundAntQuery | CompoundDoubledSyllableQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.PREFIX_WILDCARD_EQUALS) {
        return executePrefixWildcardEquals(
          parsed as PrefixWildcardEqualsQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.PARTIAL_RHYME_MASK) {
        return executePartialRhymeMaskQuery(
          parsed as PartialRhymeMaskQuery,
          db,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.PARTIAL_INITIAL_MASK) {
        return executePartialInitialMaskQuery(
          parsed as PartialInitialMaskQuery,
          db,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.SERIAL_PHONEME) {
        return executeSerialPhonemeQuery(
          parsed as SerialPhonemeAnchorQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.HYBRID_CODE) {
        return executeHybridCodeQuery(
          parsed as HybridCodeQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.LITERAL_REF) {
        return executeLiteralRefQuery(
          parsed as LiteralRefQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.PLUS_ANCHOR) {
        return executePlusAnchorQuery(
          parsed as PlusAnchorQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      if (parsed.kind === QueryKind.MASK) {
        return executeMaskQuery(parsed as MaskQuery, db, mode, limit, offset);
      }
      if (parsed.kind === QueryKind.RHYME_ANCHOR) {
        return executeRhymeAnchorQuery(parsed as RhymeAnchorQuery, db, limit, offset);
      }
      if (parsed.kind === QueryKind.JYUTPING_ANCHOR) {
        return executeJyutpingAnchorQuery(
          parsed as JyutpingAnchorQuery,
          db,
          mode,
          limit,
          offset,
        );
      }
      // Handle equals queries
      if (parsed.kind === QueryKind.EQUALS) {
        return executeEqualsQuery(parsed as EqualsQuery, db, mode, limit, offset);
      }
      // ponytail: HYBRID_TAIL_EQUALS_ALIAS 暫走 stub；MF-4 改 executeMatchSpec
      if (parsed.kind === QueryKind.HYBRID_TAIL_EQUALS_ALIAS) {
        return executeMaskFamilyStub(
          { kind: QueryKind.MASK, raw_q: (parsed as HybridTailEqualsAliasQuery).hybrid_q },
          db, mode, limit, offset
        );
      }
      // ponytail: WILDCARD_CODE_ANCHOR | TRIPLE_RHYME_ANCHOR | CODE_REF_MIDDLE_RHYME → stub until MF-4
      return executeMaskFamilyStub(parsed, db, mode, limit, offset);
    
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

function matchesEqualsPhonemeSpan(
  word: WordRow,
  refParts: string[],
  startPos: number,
  opts: {
    phoneme_anchor_only: boolean;
    ref_literal: string;
    dimension: EqualsDimension;
  },
): boolean {
  const charText = String(word.char ?? '');
  if (!opts.phoneme_anchor_only && opts.ref_literal && !charText.includes(opts.ref_literal)) {
    return false;
  }
  const isFinal = opts.dimension === 'final' || opts.dimension === 'rhyme';
  const wordParts = isFinal ? getRhymeFinals(word) : getWordParts(word, 'initials');
  if (!wordParts.length) {
    return false;
  }
  for (let i = 0; i < refParts.length; i++) {
    const pos = startPos + i;
    if (pos >= wordParts.length) {
      return false;
    }
    if (refParts[i] && refParts[i] !== wordParts[pos]) {
      return false;
    }
  }
  return true;
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

/** ponytail: infer ref phoneme when exact row missing — scan words containing literal */
function inferRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping FROM words WHERE char LIKE ? LIMIT 200',
  );
  stmt.bind([`%${literal}%`]);
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const text = String(row.char ?? '');
    const idx = text.indexOf(literal);
    if (idx < 0) {
      continue;
    }
    const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (!parts.length || idx >= parts.length) {
      continue;
    }
    if (literal.length === 1) {
      stmt.free();
      return [parts[idx]!];
    }
  }
  stmt.free();
  return null;
}

function equalsRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const row = equalsAuthoritativeRow(db, literal);
  if (row) {
    const isFinal = dimension === 'final' || dimension === 'rhyme';
    const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
    return parts.length ? parts : null;
  }
  return inferRefPhonemeParts(db, literal, dimension);
}

function phonemePartsSuffix(
  row: WordRow,
  dimension: EqualsDimension,
  suffixLen: number,
): string[] | null {
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
  if (!parts.length || parts.length < suffixLen) {
    return null;
  }
  return parts.slice(-suffixLen);
}

/** Port of suffix_aligned_ref_phoneme_parts — ponytail: first pool row, not pron_rank sort */
function suffixAlignedRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const refLen = literal.length;
  if (refLen < 2) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }

  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping, length FROM words WHERE char LIKE ? LIMIT 500',
  );
  stmt.bind([`%${literal}`]);
  const suffixRows: WordRow[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    if (String(row.char ?? '').endsWith(literal)) {
      suffixRows.push(row);
    }
  }
  stmt.free();

  const longer = suffixRows.filter((r) => String(r.char ?? '').length > refLen);
  const exact = suffixRows.filter((r) => String(r.char ?? '').length === refLen);
  const pool = longer.length ? longer : exact;
  if (!pool.length) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }

  return phonemePartsSuffix(pool[0]!, dimension, refLen);
}

function buildPrefixWildcardEqualsSpec(
  parsed: PrefixWildcardEqualsQuery,
): (MatchSpec & { equals_span: EqualsSpan }) | null {
  const inner = buildEqualsMatchSpec(parsed.inner_q);
  if (!inner?.equals_span) {
    return null;
  }
  return {
    width: parsed.width,
    code_prefix: inner.code_prefix,
    equals_span: {
      ref_literal: inner.equals_span.ref_literal,
      start_pos: 1,
      dimension: inner.equals_span.dimension,
      phoneme_anchor_only: true,
      whole_word: false,
    },
  };
}

function executePrefixWildcardEquals(
  parsed: PrefixWildcardEqualsQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const spec = buildPrefixWildcardEqualsSpec(parsed);
  if (!spec?.equals_span) {
    return { items: [], hint: '無效的前綴通配等號查詢' };
  }

  const span = spec.equals_span;
  const targetParts = suffixAlignedRefPhonemeParts(db, span.ref_literal, span.dimension);
  if (!targetParts) {
    return { items: [] };
  }

  const width = spec.width;
  const fullCode = spec.code_prefix || '';
  const variants = fullCode ? getCodeVariants(fullCode, normalizeSearchMode(mode)) : [];

  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const params: (string | number)[] = [width, width];
  if (variants.length) {
    sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
    params.push(...variants);
  }
  sql += ' LIMIT 2000';

  const stmt = db.prepare(sql);
  stmt.bind(params);
  const matched: QueryResult[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    if (!wordMatchesWidth(word, width)) {
      continue;
    }
    if (
      matchesEqualsPhonemeSpan(word, targetParts, span.start_pos, {
        phoneme_anchor_only: span.phoneme_anchor_only,
        ref_literal: span.ref_literal,
        dimension: span.dimension,
      })
    ) {
      matched.push(rowToResult(word));
    }
  }
  stmt.free();

  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

function wordMatchesWidth(row: WordRow, width: number): boolean {
  const stored = Number(row.length ?? 0);
  if (stored > 0) {
    return stored === width;
  }
  return String(row.char ?? '').length === width;
}

/** Code-anchored equals (e.g. 2=我3, 34=我) — port of query_words_by_equals_spec non-whole-word branch */
function executeCodeAnchoredEquals(
  spec: MatchSpec & { equals_span: EqualsSpan },
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): SearchResult {
  const span = spec.equals_span;
  const refParts = equalsRefPhonemeParts(db, span.ref_literal, span.dimension);
  if (!refParts) {
    return { items: [] };
  }

  const fullCode = spec.code_prefix || '';
  const variants = fullCode ? getCodeVariants(fullCode, normalizeSearchMode(mode)) : [];
  const width = spec.width;

  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const params: (string | number)[] = [width, width];

  if (variants.length) {
    sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
    params.push(...variants);
  }

  sql += ' LIMIT 2000';
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const candidates: WordRow[] = [];
  while (stmt.step()) {
    candidates.push(stmt.getAsObject() as WordRow);
  }
  stmt.free();

  const matched: QueryResult[] = [];
  for (const word of candidates) {
    if (!wordMatchesWidth(word, width)) {
      continue;
    }
    if (
      matchesEqualsPhonemeSpan(word, refParts, span.start_pos, {
        phoneme_anchor_only: span.phoneme_anchor_only,
        ref_literal: span.ref_literal,
        dimension: span.dimension,
      })
    ) {
      matched.push(rowToResult(word));
    }
  }
  return { items: sortQueryResults(matched).slice(offset, offset + limit) };
}

/**
 * Whole-word equals (e.g. 香港=) — match words sharing ref finals/initials JSON (P1).
 * ponytail: uses stored finals/initials columns; full port uses rhyme tuple compare in filters.py
 */
function executeWholeWordEquals(
  spec: MatchSpec & { equals_span: EqualsSpan },
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  const span = spec.equals_span;
  const isFinal = span.dimension === 'final' || span.dimension === 'rhyme';
  const field = isFinal ? 'finals' : 'initials';

  const refStmt = db.prepare(
    `SELECT char, jyutping, code, finals, initials, length FROM words WHERE char = ? LIMIT 1`,
  );
  refStmt.bind([span.ref_literal]);
  const refRow = refStmt.step() ? refStmt.getAsObject() : null;
  refStmt.free();

  if (!refRow) {
    return { items: [] };
  }

  const phonemeKey = String(refRow[field] ?? '');
  if (!phonemeKey) {
    return { items: [] };
  }

  const width = spec.width;
  let sql = `
    SELECT char, jyutping, code
    FROM words
    WHERE ${field} = ?
      AND (
        length = ?
        OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
  `;
  const params: (string | number)[] = [phonemeKey, width, width];

  if (spec.code_prefix) {
    const variants = getCodeVariants(spec.code_prefix, normalizeSearchMode(mode));
    const placeholders = variants.map(() => '?').join(', ');
    sql += ` AND code IN (${placeholders})`;
    params.push(...variants);
  }

  sql += ' ORDER BY char LIMIT ? OFFSET ?';
  params.push(limit, offset);

  const stmt = db.prepare(sql);
  stmt.bind(params);
  const results: QueryResult[] = [];
  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();

  return { items: results };
}

/**
 * Execute equals query (e.g., 2=我3, 香港=, =香, 就=)
 * This implements the equals query syntax for finding words with matching rhymes/initials
 */
async function executeEqualsQuery(
  parsed: EqualsQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): Promise<SearchResult> {
  // Build MatchSpec for the equals query
  const spec = buildEqualsMatchSpec(parsed.raw_q);
  
  if (!spec) {
    return { items: [], hint: '無效的等號查詢語法' };
  }
  
  const span = spec.equals_span;
  const { ref_literal, dimension, whole_word } = span;
  const code_prefix = spec.code_prefix;

  if (whole_word) {
    const items = executeWholeWordEquals(
      spec as MatchSpec & { equals_span: EqualsSpan },
      db,
      mode,
      limit,
      offset,
    ).items;
    if (items.length === 0 && code_prefix) {
      const hint = await codePrefixedWholeWordEqualsEmptyHint(spec, db);
      return { items: [], hint: hint || '未找到符合的結果' };
    }
    return { items };
  }

  // Code-anchored equals (e.g. 2=我3, 34=我, 2我=3)
  if (code_prefix && ref_literal) {
    return executeCodeAnchoredEquals(spec, db, mode, limit, offset);
  }
  
  // Case 3: equals + word (e.g., =香)
  if (!code_prefix && ref_literal && dimension === 'initial') {
    // Match words with same initial as reference word
    const refSql = 'SELECT jyutping FROM words WHERE char = ?';
    const refStmt = db.prepare(refSql);
    refStmt.bind([ref_literal]);
    const refRow = refStmt.step() ? refStmt.getAsObject() : null;
    refStmt.free();
    
    if (refRow && refRow.jyutping) {
      // Extract first character of jyutping for initial matching
      const initial = refRow.jyutping.charAt(0);
      const sql = `
        SELECT char, jyutping, code
        FROM words
        WHERE jyutping LIKE ?
        ORDER BY char
        LIMIT ? OFFSET ?
      `;
      const stmt = db.prepare(sql);
      stmt.bind([`${initial}%`, limit, offset]);
      
      const results: QueryResult[] = [];
      while (stmt.step()) {
        results.push(rowToResult(stmt.getAsObject()));
      }
      stmt.free();
      
      return { items: results };
    }
  }
  
  // Case 4: word + equals (e.g., 就=)
  if (code_prefix && ref_literal && dimension === 'final') {
    // Similar to case 3 but for final matching
    const refSql = 'SELECT jyutping FROM words WHERE char = ?';
    const refStmt = db.prepare(refSql);
    refStmt.bind([ref_literal]);
    const refRow = refStmt.step() ? refStmt.getAsObject() : null;
    refStmt.free();
    
    if (refRow && refRow.jyutping) {
      // For now, use simple pattern matching
      const sql = `
        SELECT char, jyutping, code
        FROM words
        WHERE jyutping LIKE ?
        ORDER BY char
        LIMIT ? OFFSET ?
      `;
      const stmt = db.prepare(sql);
      stmt.bind([`%${String(refRow.jyutping).slice(-1)}`, limit, offset]);
      
      const results: QueryResult[] = [];
      while (stmt.step()) {
        results.push(rowToResult(stmt.getAsObject()));
      }
      stmt.free();
      
      return { items: results };
    }
  }
  
  // Fallback: try simple text search
  return executeMaskFamilyStub(parsed, db, mode, limit, offset);
}

/**
 * Transitional LIKE stub — not Python execute_match_spec (ADR-0024 §6 MF-0).
 * ponytail: ceiling = SQL LIKE on code/char; upgrade path = executeMatchSpec via MF-4…MF-6.
 */
function executeMaskFamilyStub(
  parsed: ParsedQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  // For now, treat as simple code matching
  // Full implementation would parse mask patterns properly
  const pattern = parsed.raw_q
    .replace(/\?/g, '_')  // ? matches single character
    .replace(/\*/g, '%')  // * matches any sequence
    .replace(/_%/g, '_');  // Clean up consecutive wildcards
  
  const sql = `
    SELECT char, jyutping, code 
    FROM words 
    WHERE code LIKE ? OR char LIKE ?
    ORDER BY char 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([pattern, pattern, limit, offset]);
  
  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();
  
  return { items: results };
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
};
