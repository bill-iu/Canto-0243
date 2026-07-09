/** QueryEngine entry — port of query_dispatch.QueryEngine */
import {
  ensureStaticRelationIndexes,
  getDatabase,
  initializeDatabase,
  isDatabaseInitialized,
} from '../init.ts';
import type { Database } from '../sqljs.ts';
import { pingZeEffectiveMode, pingZeModeRedirectHint } from '../ping-zak.ts';
import { QueryKind } from '../query-kind.ts';
import type { ParsedQuery, QueryMode, QueryResult, SearchContext, SearchResult } from '../query-types.ts';
import { normalizeAndParse, normalizeQuery } from './parse.ts';
import { dispatchParsed, executeListFilter } from './dispatch.ts';
import { dispatchSynMode } from './mode-dispatch.ts';

export class QueryEngine {
  private db: Database | null = null;

  async execute(ctx: SearchContext): Promise<SearchResult> {
    if (!isDatabaseInitialized()) {
      await initializeDatabase();
    }
    this.db = getDatabase();

    if (!this.db) {
      return { items: [], hint: '資料庫初始化失敗' };
    }

    const dbCtx = { ...ctx, db: this.db };

    if (!ctx.q) {
      return executeListFilter(this.db, ctx);
    }

    const q = normalizeQuery(ctx.q);

    if (ctx.mode === 'syn') {
      await ensureStaticRelationIndexes();
      return dispatchSynMode({ ...ctx, q }, dbCtx);
    }

    const parsed = normalizeAndParse(ctx.q);
    const redirected = this.maybeRedirectPingZe(parsed, dbCtx);
    if (redirected) {
      return redirected;
    }
    if (parsed.kind === QueryKind.RELATION_LOOKUP) {
      await ensureStaticRelationIndexes();
    }
    return await dispatchParsed(parsed, dbCtx);
  }

  private maybeRedirectPingZe(
    parsed: ParsedQuery,
    ctx: SearchContext & { db: Database },
  ): Promise<SearchResult> | null {
    if (parsed.kind !== QueryKind.PING_ZE_SERIAL) {
      return null;
    }
    const effective = pingZeEffectiveMode();
    if (ctx.mode === 'm2' || ctx.mode === '02493' || ctx.mode === effective) {
      return null;
    }
    return dispatchParsed(parsed, { ...ctx, mode: effective, offset: 0 }).then((result) => ({
      items: result.items,
      total: result.total,
      hint: pingZeModeRedirectHint(effective, ctx.ui_lang ?? 'zh') ?? undefined,
      effective_mode: effective,
      cache_path: result.cache_path,
    }));
  }
}

export const queryEngine = new QueryEngine();

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

export async function executeSearch(ctx: SearchContext): Promise<SearchResult> {
  return queryEngine.execute(ctx);
}
