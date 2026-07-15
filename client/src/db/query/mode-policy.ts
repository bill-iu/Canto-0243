/**
 * 搜尋模式轉接決策 — ModePolicy（結果無副作用）。
 * Port of app/services/query_mode_policy.py
 *
 * Detect: regex (mode-detect) + full-parse (normalizeAndParse) as adapters.
 */
import type { QueryMode } from '../query-types.ts';
import { modeRedirectHint } from '../../mode-meta.ts';
import { isRelationSyntaxQuery } from './mode-detect.ts';
import { normalizeAndParse, resolveFallback0243Mode } from './parse.ts';
import { QueryKind } from '../query-kind.ts';

export type DetectKind = 'full' | 'regex';

export type ModeRedirectPlan = {
  should_redirect: boolean;
  effective_mode: 'm1' | 'm2' | 'm3' | null;
  hint: string | null;
  reset_offset: boolean;
};

function isRelationFullParse(q: string): boolean {
  const parsed = normalizeAndParse(q);
  return (
    parsed.kind === QueryKind.RELATION_LOOKUP ||
    parsed.kind === QueryKind.COMPOUND_SYN ||
    parsed.kind === QueryKind.COMPOUND_ANT ||
    parsed.kind === QueryKind.COMPOUND_CONNECT_SYN ||
    parsed.kind === QueryKind.COMPOUND_CONNECT_ANT
  );
}

function detectRelation(q: string, detect: DetectKind): boolean {
  return detect === 'regex' ? isRelationSyntaxQuery(q) : isRelationFullParse(q);
}

export function planRedirect(
  q: string,
  opts: {
    currentMode: string;
    fallback0243Mode?: QueryMode | string | null;
    detect?: DetectKind;
    isRelation?: boolean;
    lang?: 'zh' | 'en';
  },
): ModeRedirectPlan {
  const detect = opts.detect ?? 'regex';
  const lang = opts.lang ?? 'zh';

  if (opts.currentMode !== 'syn') {
    return {
      should_redirect: false,
      effective_mode: null,
      hint: null,
      reset_offset: false,
    };
  }

  const relation =
    opts.isRelation !== undefined ? opts.isRelation : detectRelation(q, detect);
  if (!relation) {
    return {
      should_redirect: false,
      effective_mode: null,
      hint: null,
      reset_offset: false,
    };
  }

  const effective = resolveFallback0243Mode(
    opts.fallback0243Mode as QueryMode | undefined,
  );
  return {
    should_redirect: true,
    effective_mode: effective,
    hint: modeRedirectHint(effective, lang),
    reset_offset: true,
  };
}

/** ponytail: self-check */
export function modePolicySelfCheck(): void {
  const idle = planRedirect('~開心', { currentMode: 'm1', detect: 'regex' });
  if (idle.should_redirect) throw new Error('modePolicySelfCheck: idle');

  const go = planRedirect('~開心', {
    currentMode: 'syn',
    fallback0243Mode: 'm2',
    detect: 'regex',
  });
  if (!go.should_redirect || go.effective_mode !== 'm2' || !go.reset_offset) {
    throw new Error(`modePolicySelfCheck: go ${JSON.stringify(go)}`);
  }
  if (!go.hint?.includes('02493')) {
    throw new Error(`modePolicySelfCheck: hint ${go.hint}`);
  }

  const pool = planRedirect('開心', { currentMode: 'syn', detect: 'regex' });
  if (pool.should_redirect) throw new Error('modePolicySelfCheck: pool');
}
