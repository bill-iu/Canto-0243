/**
 * SearchSession — thin commit plan over ModePolicy.
 * Owns mode + pzmode + fallback + commitSearch redirect fields.
 * Does not own tabs / history / readiness gate.
 */
import type { QueryMode } from '../query-types.ts';
import { planRedirect } from './mode-policy.ts';

export type CommitSearchPlan = {
  q: string;
  mode: string;
  pzmode?: 'm1' | 'm2' | 'm3';
  offset: number;
  fallback0243Mode: 'm1' | 'm2' | 'm3';
  redirectHint: string | null;
};

function asM123(fallback?: QueryMode | string | null): 'm1' | 'm2' | 'm3' {
  if (fallback === 'm2' || fallback === '02493') return 'm2';
  if (fallback === 'm3' || fallback === '394052') return 'm3';
  return 'm1';
}

export function planCommitSearch(input: {
  q: string;
  mode: string;
  last0243Mode?: QueryMode | string | null;
  pzmode?: 'm1' | 'm2' | 'm3';
  lang?: 'zh' | 'zh-Hans' | 'en';
}): CommitSearchPlan {
  const fallback = asM123(input.last0243Mode);
  const plan = planRedirect(input.q, {
    currentMode: input.mode,
    fallback0243Mode: fallback,
    detect: 'regex',
    lang: input.lang ?? 'zh',
  });
  return {
    q: input.q,
    mode: plan.should_redirect ? (plan.effective_mode as string) : input.mode,
    pzmode: input.pzmode,
    offset: plan.reset_offset ? 0 : 0,
    fallback0243Mode: fallback,
    redirectHint: plan.should_redirect ? plan.hint : null,
  };
}
