/**
 * 搜尋模式轉接決策 — portable ModePolicy（結果無副作用）。
 * Mirrors client/src/db/query/mode-policy.ts (regex detect path for 介面轉接).
 */
import { isRelationSyntaxQuery } from "./query-mode-detect.mjs";
import { MODE_META, modeRedirectHint } from "./mode-i18n.mjs";

/**
 * @param {string} q
 * @param {{ currentMode: string, fallback0243Mode?: string, lang?: string, isRelation?: boolean }} opts
 */
export function planRedirect(q, opts) {
  const lang = opts.lang || "zh";
  if (opts.currentMode !== "syn") {
    return { should_redirect: false, effective_mode: null, hint: null, reset_offset: false };
  }
  const relation =
    opts.isRelation !== undefined ? opts.isRelation : isRelationSyntaxQuery(q);
  if (!relation) {
    return { should_redirect: false, effective_mode: null, hint: null, reset_offset: false };
  }
  const raw = opts.fallback0243Mode;
  const effective = MODE_META[raw] && (raw === "m1" || raw === "m2" || raw === "m3") ? raw : "m1";
  return {
    should_redirect: true,
    effective_mode: effective,
    hint: modeRedirectHint(effective, lang),
    reset_offset: true,
  };
}

/**
 * SearchSession — thin commit plan over ModePolicy.
 * @param {{ q: string, mode: string, last0243Mode?: string, pzmode?: string, lang?: string }} input
 */
export function planCommitSearch(input) {
  const plan = planRedirect(input.q, {
    currentMode: input.mode,
    fallback0243Mode: input.last0243Mode || "m1",
    lang: input.lang || "zh",
  });
  const mode = plan.should_redirect ? plan.effective_mode : input.mode;
  return {
    q: input.q,
    mode,
    pzmode: input.pzmode,
    offset: plan.reset_offset ? 0 : 0,
    fallback0243Mode: input.last0243Mode || "m1",
    redirectHint: plan.should_redirect ? plan.hint : null,
  };
}
