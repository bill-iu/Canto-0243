/** QueryKind metadata: route + MatchSpec (single source; ADR-0002). */
import { QueryKind, RouteKind } from './query-kind.ts';

export interface QueryKindMeta {
  route: RouteKind;
  match_spec?: boolean;
}

export const QUERY_KIND_META: Record<QueryKind, QueryKindMeta> = {
  [QueryKind.RELATION_LOOKUP]: { route: RouteKind.RELATION },
  [QueryKind.COMPOUND_SYN]: { route: RouteKind.MASK_FAMILY, match_spec: true },
  [QueryKind.COMPOUND_ANT]: { route: RouteKind.MASK_FAMILY, match_spec: true },
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
  [QueryKind.PING_ZE_SERIAL]: { route: RouteKind.DIGIT },
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
