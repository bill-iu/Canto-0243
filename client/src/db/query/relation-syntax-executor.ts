/** Relation syntax page execution — mirror of RelationSyntaxExecutor. */
import type { Database } from '../sqljs.ts';
import { relationLookupItems } from '../relation-pool/index.ts';
import type { RelationPoolItem } from '../relation-pool/index.ts';
import type { QueryMode, QueryResult, RelationLookupQuery, SearchResult } from '../query-types.ts';

export function poolItemToResult(item: RelationPoolItem): QueryResult {
  return {
    word: item.char,
    jyutping: item.jyutping,
    code: item.code,
    score: item.score ?? 0,
    relation: item.relation,
    in_db: item.in_db,
    source: item.source,
  };
}

export async function executeRelationLookup(
  parsed: RelationLookupQuery,
  db: Database,
  mode: QueryMode,
  limit: number,
  offset: number,
): Promise<SearchResult> {
  const seed = parsed.word.trim();
  if (!seed) {
    return { items: [] };
  }

  const rows = await relationLookupItems(
    db,
    seed,
    parsed.relation_kind,
    mode,
    parsed.code_prefix,
    limit,
    offset,
  );

  return {
    items: rows.map(poolItemToResult),
  };
}
