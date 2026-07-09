/** 搜尋模式轉接 — port of query_mode_dispatch (predicate table). */
import type { Database } from '../sqljs.ts';
import { pingZeEffectiveMode, pingZeModeRedirectHint } from '../ping-zak.ts';
import { isJyutpingQuery } from '../jyutping-match.ts';
import { relationPoolPage } from '../relation-pool.ts';
import type { SearchContext, SearchResult } from '../query-types.ts';
import {
  JYUTPING_SYN_MODE_HINT,
  modeRedirectHint,
  normalizeAndParse,
  resolveFallback0243Mode,
} from './parse.ts';
import { isPingZeSerialQuery, isRelationSyntaxQuery } from './mode-detect.ts';
import { dispatchParsed, poolItemToResult } from './dispatch.ts';

export type SynModeCtx = SearchContext & { q: string };
export type SynModeDbCtx = SearchContext & { db: Database };

export async function dispatchSynMode(
  ctx: SynModeCtx,
  dbCtx: SynModeDbCtx,
): Promise<SearchResult> {
  const { q, limit, offset, db } = dbCtx;

  if (isJyutpingQuery(q)) {
    return { items: [], hint: JYUTPING_SYN_MODE_HINT };
  }

  if (isRelationSyntaxQuery(q)) {
    const effective = resolveFallback0243Mode(ctx.fallback_0243_mode);
    const parsed = normalizeAndParse(q);
    const result = await dispatchParsed(parsed, { ...dbCtx, mode: effective, offset: 0 });
    return {
      items: result.items,
      total: result.total,
      hint: modeRedirectHint(effective, ctx.ui_lang ?? 'zh'),
      effective_mode: effective,
      cache_path: result.cache_path,
    };
  }

  if (isPingZeSerialQuery(q)) {
    const effective = pingZeEffectiveMode();
    const parsed = normalizeAndParse(q);
    const result = await dispatchParsed(parsed, { ...dbCtx, mode: effective, offset: 0 });
    return {
      items: result.items,
      total: result.total,
      hint: pingZeModeRedirectHint(effective, ctx.ui_lang ?? 'zh') ?? undefined,
      effective_mode: effective,
      cache_path: result.cache_path,
    };
  }

  const page = await relationPoolPage(db, q, limit, offset);
  return { items: page.map(poolItemToResult) };
}
