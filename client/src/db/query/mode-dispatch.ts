/** 搜尋模式轉接 — port of query_mode_dispatch (predicate table). */
import type { Database } from '../sqljs.ts';
import { isJyutpingQuery } from '../jyutping-match.ts';
import { relationPoolPage } from '../relation-pool/index.ts';
import type { SearchContext, SearchResult } from '../query-types.ts';
import { JYUTPING_SYN_MODE_HINT, normalizeAndParse } from './parse.ts';
import { dispatchParsed } from './dispatch.ts';
import { poolItemToResult } from './relation-syntax-executor.ts';
import { planRedirect } from './mode-policy.ts';

export type SynModeCtx = SearchContext & { q: string };
export type SynModeDbCtx = SearchContext & { db: Database };

export async function dispatchSynMode(
  ctx: SynModeCtx,
  dbCtx: SynModeDbCtx,
): Promise<SearchResult> {
  const { limit, offset, db } = dbCtx;
  const q = dbCtx.q!;

  if (isJyutpingQuery(q)) {
    return { items: [], hint: JYUTPING_SYN_MODE_HINT };
  }

  const plan = planRedirect(q, {
    currentMode: 'syn',
    fallback0243Mode: ctx.fallback_0243_mode,
    detect: 'full',
    lang: ctx.ui_lang ?? 'zh',
  });
  if (plan.should_redirect) {
    const effective = plan.effective_mode ?? 'm1';
    const parsed = normalizeAndParse(q);
    const result = await dispatchParsed(parsed, {
      ...dbCtx,
      mode: effective,
      offset: plan.reset_offset ? 0 : offset,
    });
    return {
      items: result.items,
      total: result.total,
      hint: plan.hint ?? undefined,
      effective_mode: effective,
      cache_path: result.cache_path,
    };
  }

  const page = await relationPoolPage(db, q, limit, offset);
  return { items: page.map(poolItemToResult) };
}
