/** AUTO-GENERATED from contracts/query-kind-manifest.json — do not edit.
 * Run: python scripts/codegen_query_kind_manifest.py
 */

export enum QueryKind {
  RELATION_LOOKUP = 'relation_lookup',
  COMPOUND_SYN = 'compound_syn',
  COMPOUND_ANT = 'compound_ant',
  COMPOUND_CONNECT_SYN = 'compound_connect_syn',
  COMPOUND_CONNECT_ANT = 'compound_connect_ant',
  COMPOUND_DOUBLED_SYLLABLE = 'compound_doubled_syllable',
  HETERONYM_CODE = 'heteronym_code',
  EQUALS = 'equals',
  PREFIX_WILDCARD_EQUALS = 'prefix_wildcard_equals',
  PARTIAL_RHYME_MASK = 'partial_rhyme_mask',
  PARTIAL_INITIAL_MASK = 'partial_initial_mask',
  SERIAL_PHONEME = 'serial_phoneme',
  PLUS_ANCHOR = 'plus_anchor',
  WILDCARD_CODE_ANCHOR = 'wildcard_code_anchor',
  CODE_REF_MIDDLE_RHYME = 'code_ref_middle_rhyme',
  LITERAL_REF = 'literal_ref',
  RHYME_ANCHOR = 'rhyme_anchor',
  TRIPLE_RHYME_ANCHOR = 'triple_rhyme_anchor',
  JYUTPING_ANCHOR = 'jyutping_anchor',
  MASK = 'mask',
  PING_ZE_SERIAL = 'ping_ze_serial',
  DIGIT_CODE = 'digit_code',
  WORD_LOOKUP = 'word_lookup',
  JYUTPING_FRAGMENT = 'jyutping_fragment',
  UNMATCHED = 'unmatched',
}

export enum RouteKind {
  DIGIT = 'digit',
  MASK_FAMILY = 'mask_family',
  HETERONYM = 'heteronym',
  RELATION = 'relation',
  LOOKUP = 'lookup',
  UNMATCHED = 'unmatched',
  EMPTY = 'empty',
}

export interface QueryKindMeta {
  route: RouteKind;
  match_spec?: boolean;
}

export const QUERY_KIND_META: Record<QueryKind, QueryKindMeta> = {
  [QueryKind.RELATION_LOOKUP]: { route: RouteKind.RELATION },
  [QueryKind.COMPOUND_SYN]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_ANT]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_CONNECT_SYN]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_CONNECT_ANT]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_DOUBLED_SYLLABLE]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.HETERONYM_CODE]: { route: RouteKind.HETERONYM },
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
  [QueryKind.MASK]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.PING_ZE_SERIAL]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.DIGIT_CODE]: { route: RouteKind.DIGIT },
  [QueryKind.WORD_LOOKUP]: { route: RouteKind.LOOKUP },
  [QueryKind.JYUTPING_FRAGMENT]: { route: RouteKind.LOOKUP },
  [QueryKind.UNMATCHED]: { route: RouteKind.UNMATCHED },
};

export const MASK_FAMILY_KINDS: ReadonlySet<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([, meta]) => meta.route === RouteKind.MASK_FAMILY)
    .map(([kind]) => kind as QueryKind),
);

export const MATCH_SPEC_KINDS: ReadonlySet<QueryKind> = new Set(
  Object.entries(QUERY_KIND_META)
    .filter(([, meta]) => Boolean(meta.match_spec))
    .map(([kind]) => kind as QueryKind),
);

export function routeKindFor(kind: QueryKind): RouteKind {
  return QUERY_KIND_META[kind]?.route ?? RouteKind.EMPTY;
}

export function usesMatchSpec(kind: QueryKind): boolean {
  return MATCH_SPEC_KINDS.has(kind);
}
