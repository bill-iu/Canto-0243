import type { QueryKind } from './query-kind.ts';

export type QueryMode = 'm1' | 'm2' | 'm3' | '0243' | '02493' | '394052' | 'syn' | 'pz';

export interface ParsedQuery {
  kind: QueryKind;
  raw_q: string;
  hint?: string;
  pzmode?: 'm1' | 'm2' | 'm3';
  anchor?: string;
  base?: ParsedQuery;
  code_prefix?: string;
  relation_kind?: 'syn' | 'ant';
  connective?: string;
  rhyme_char?: string;
  word?: string;
}

export interface PingZeSerialQuery extends ParsedQuery {
  kind: QueryKind.PING_ZE_SERIAL;
  raw_q: string;
  pzmode: 'm1' | 'm2' | 'm3';
  anchor?: string;
  base?: ParsedQuery;
}

export interface DigitCodeQuery extends ParsedQuery {
  kind: QueryKind.DIGIT_CODE;
  raw_q: string;
}

export interface WordLookupQuery extends ParsedQuery {
  kind: QueryKind.WORD_LOOKUP;
  raw_q: string;
}

export interface JyutpingFragmentQuery extends ParsedQuery {
  kind: QueryKind.JYUTPING_FRAGMENT;
  raw_q: string;
}

export interface MaskQuery extends ParsedQuery {
  kind: QueryKind.MASK;
  raw_q: string;
}

export interface RhymeAnchorQuery extends ParsedQuery {
  kind: QueryKind.RHYME_ANCHOR;
  raw_q: string;
  constraint: 'final' | 'initial';
  anchor_pos: number;
  anchor: string;
  slots: string;
  width: number;
}

export interface PrefixWildcardEqualsQuery extends ParsedQuery {
  kind: QueryKind.PREFIX_WILDCARD_EQUALS;
  raw_q: string;
  inner_q: string;
  ref_literal: string;
  width: number;
}

export interface PartialRhymeMaskQuery extends ParsedQuery {
  kind: QueryKind.PARTIAL_RHYME_MASK;
  raw_q: string;
  pattern: string;
  width: number;
  anchors: Array<[number, string]>;
}

export interface PartialInitialMaskQuery extends ParsedQuery {
  kind: QueryKind.PARTIAL_INITIAL_MASK;
  raw_q: string;
  pattern: string;
  width: number;
  anchors: Array<[number, string]>;
}

export interface SerialPhonemeAnchorQuery extends ParsedQuery {
  kind: QueryKind.SERIAL_PHONEME;
  raw_q: string;
  width: number;
  constraint: 'final' | 'initial';
  code_slots: Array<[number, string]>;
  anchors: Array<[number, string]>;
  mask: string;
}

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

export interface LiteralRefQuery extends ParsedQuery {
  kind: QueryKind.LITERAL_REF;
  raw_q: string;
  code_digits: string;
  literal_char: string;
  literal_pos: number;
  width: number;
}

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

export interface CompoundConnectSynQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_CONNECT_SYN;
  raw_q: string;
  code_prefix?: string;
  connective: string;
  rhyme_char?: string;
}

export interface CompoundConnectAntQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_CONNECT_ANT;
  raw_q: string;
  code_prefix?: string;
  connective: string;
  rhyme_char?: string;
}

export interface CompoundDoubledSyllableQuery extends ParsedQuery {
  kind: QueryKind.COMPOUND_DOUBLED_SYLLABLE;
  raw_q: string;
  width: number;
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

export interface RelationLookupQuery extends ParsedQuery {
  kind: QueryKind.RELATION_LOOKUP;
  raw_q: string;
  relation_kind: 'syn' | 'ant';
  word: string;
  code_prefix?: string;
}

export interface UnmatchedQuery extends ParsedQuery {
  kind: QueryKind.UNMATCHED;
  raw_q: string;
  hint?: string;
}

export interface QueryResult {
  word: string;
  jyutping: string;
  code: string;
  definition?: string;
  score: number;
  char?: string;
  display_text?: string;
  /** ponytail: lookup layout row kind — upgrade path: full lookup_layout.ts module */
  resultType?: 'code' | 'jyutping' | 'word';
  heteronym_tags?: string[];
  anchor_dimension?: 'initial' | 'final';
  relation?: 'syn' | 'ant' | 'semantic_related';
  in_db?: boolean;
  source?: string;
}

export interface SearchContext {
  q: string | null;
  code?: string;
  char?: string;
  mode: QueryMode;
  pzmode?: 'm1' | 'm2' | 'm3';
  limit: number;
  offset: number;
  fallback_0243_mode?: QueryMode;
  ui_lang?: 'zh' | 'zh-Hans' | 'en';
  /** Cooperative cancel — engine hot paths throw SearchCancelledError when true */
  shouldCancel?: () => boolean;
}

export interface SearchResult {
  items: QueryResult[];
  total?: number;
  hint?: string;
  cache_path?: string;
  effective_mode?: QueryMode;
  /** 純漢字詞條 lookup：只輸出詞列（PWA 詞條行已含碼／粵拼；見 CONTEXT 詞條 lookup 版面） */
  lookup_layout?: boolean;
}
