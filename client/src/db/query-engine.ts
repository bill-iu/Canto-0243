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

/** Hybrid code query (23就) */
export interface HybridCodeQuery extends ParsedQuery {
  kind: QueryKind.HYBRID_CODE;
  raw_q: string;
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

/**
 * Parse query and classify into QueryKind
 */
export function parseQuery(q: string): ParsedQuery {
  const normalized = normalizeQuery(q);
  
  // Check for relation syntax (syn/ant queries)
  // This is a simplified version - full implementation in Python has complex patterns
  if (normalized.startsWith('~') || normalized.startsWith('！') || 
      normalized.startsWith('!') || normalized.startsWith('～')) {
    return {
      kind: QueryKind.RELATION_LOOKUP,
      raw_q: normalized,
      relation_kind: normalized.startsWith('~') || normalized.startsWith('～') ? 'syn' : 'ant',
      word: normalized.slice(1),
    } as RelationLookupQuery;
  }
  
  // Prefix wildcard equals (?困潦倒=) — before framed equals / mask
  const prefixWildcard = parsePrefixWildcardEqualsQuery(normalized);
  if (prefixWildcard) {
    return prefixWildcard;
  }

  const partialRhyme = parsePartialRhymeMaskQuery(normalized);
  if (partialRhyme) {
    return partialRhyme;
  }

  // Check for hybrid tail equals alias (e.g., 23就=)
  if (isHybridTailEqualsAlias(normalized)) {
    return {
      kind: QueryKind.HYBRID_TAIL_EQUALS_ALIAS,
      raw_q: normalized,
      hybrid_q: hybridQueryFromTailEquals(normalized),
    } as HybridTailEqualsAliasQuery;
  }
  
  // Check for framed equals query (e.g., 香港=, 2=我3)
  if (isFramedEqualsQuery(normalized)) {
    return { kind: QueryKind.EQUALS, raw_q: normalized } as EqualsQuery;
  }

  const rhymeAnchor = parseRhymeAnchorQuery(normalized);
  if (rhymeAnchor) {
    return rhymeAnchor;
  }

  const hybridCode = parseHybridCodeQuery(normalized);
  if (hybridCode) {
    return hybridCode;
  }

  if (looksLikeMaskQuery(normalized)) {
    return { kind: QueryKind.MASK, raw_q: normalized };
  }
  
  // Check for pure digit codes
  if (isPureDigits(normalized)) {
    return { kind: QueryKind.DIGIT_CODE, raw_q: normalized };
  }
  
  // Check for Chinese characters (word lookup)
  if (hasChineseChars(normalized)) {
    return { kind: QueryKind.WORD_LOOKUP, raw_q: normalized };
  }
  
  // Check for jyutping (contains letters)
  if (hasJyutpingChars(normalized)) {
    return { kind: QueryKind.JYUTPING_FRAGMENT, raw_q: normalized };
  }
  
  // Unmatched
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
  if (!m) {
    return null;
  }
  return { kind: QueryKind.HYBRID_CODE, raw_q: q };
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

  matched.sort((a, b) => a.word.localeCompare(b.word, 'zh-Hant'));
  return { items: matched.slice(offset, offset + limit) };
}

/** ponytail: stub — next step ports filter_hybrid_ref_candidates */
function executeHybridCodeQuery(
  _parsed: HybridCodeQuery,
  _db: Database,
  _mode: QueryMode,
  _limit: number,
  _offset: number,
): SearchResult {
  return { items: [] };
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

/** Port of query_grammar/rhyme.parse_rhyme_anchor_query (P1 subset) */
export function parseRhymeAnchorQuery(q: string): RhymeAnchorQuery | null {
  if (!q || q.includes(CODE_TAIL_MIDDLE) || q.includes('@') || isFramedEqualsQuery(q)) {
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

  matched.sort((a, b) => a.word.localeCompare(b.word, 'zh-Hant'));
  return { items: matched.slice(offset, offset + limit) };
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

  matched.sort((a, b) => a.word.localeCompare(b.word, 'zh-Hant'));
  return { items: matched.slice(offset, offset + limit) };
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
      if (parsed.kind === QueryKind.HYBRID_CODE) {
        return executeHybridCodeQuery(
          parsed as HybridCodeQuery,
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
      // Handle equals queries
      if (parsed.kind === QueryKind.EQUALS) {
        return executeEqualsQuery(parsed as EqualsQuery, db, mode, limit, offset);
      }
      // Handle hybrid tail equals alias
      if (parsed.kind === QueryKind.HYBRID_TAIL_EQUALS_ALIAS) {
        return executeMaskFamily(
          { kind: QueryKind.MASK, raw_q: (parsed as HybridTailEqualsAliasQuery).hybrid_q },
          db, mode, limit, offset
        );
      }
      return executeMaskFamily(parsed, db, mode, limit, offset);
    
    case RouteKind.RELATION:
      if (parsed.kind === QueryKind.RELATION_LOOKUP) {
        return executeRelationLookup(parsed as RelationLookupQuery, db, mode, limit, offset);
      }
      break;
    
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

/**
 * Execute word lookup query
 */
function executeWordLookup(
  parsed: WordLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  const sql = `
    SELECT char, jyutping, code 
    FROM words 
    WHERE char = ?
    ORDER BY char 
    LIMIT ? OFFSET ?
  `;
  
  const stmt = db.prepare(sql);
  const results: QueryResult[] = [];
  
  stmt.bind([parsed.raw_q, limit, offset]);
  
  while (stmt.step()) {
    results.push(rowToResult(stmt.getAsObject()));
  }
  stmt.free();
  
  return { items: results };
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
  // ponytail: no jyutping derive yet — upgrade path: rhyme_finals_from_jyutping
  return [];
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

  matched.sort((a, b) => a.word.localeCompare(b.word, 'zh-Hant'));
  return { items: matched.slice(offset, offset + limit) };
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
  matched.sort((a, b) => a.word.localeCompare(b.word, 'zh-Hant'));
  return { items: matched.slice(offset, offset + limit) };
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
  return executeMaskFamily(parsed, db, mode, limit, offset);
}

/**
 * Execute mask family query (contains wildcards)
 */
function executeMaskFamily(
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

/**
 * Execute relation lookup query (synonym/antonym)
 */
function executeRelationLookup(
  parsed: RelationLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number
): SearchResult {
  // This is a placeholder - full implementation would use word_relations table
  // For now, just return empty results
  return {
    items: [],
    hint: '近反義模式功能正在開發中...',
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
   * Dispatch synonym mode queries
   */
  private async dispatchSynMode(ctx: SearchContext & { q: string }, dbCtx: SearchContext & { db: Database }): Promise<SearchResult> {
    // For now, treat syn mode like normal search but with relation queries
    // Full implementation would handle mode switching and relation lookup
    const parsed = normalizeAndParse(ctx.q);
    return await dispatch(parsed, dbCtx);
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
