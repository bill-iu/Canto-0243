/**
 * UI locale policy shared by PWA and Desktop.
 *
 * The module keeps locale detection and catalog fallback at one seam. Domain
 * catalogs remain separate so callers do not need to know the storage shape.
 */

/** @typedef {'zh' | 'zh-Hans' | 'en'} UiLang */

const SIMPLIFIED_LOCALES = new Set(['zh-hans', 'zh-cn', 'zh-sg']);
const TRADITIONAL_LOCALES = new Set(['zh-hant', 'zh-hk', 'zh-mo', 'zh-tw']);

/**
 * @param {unknown} value
 * @param {UiLang} [fallback]
 * @returns {UiLang}
 */
export function normalizeUiLang(value, fallback = 'zh') {
  const raw = String(value ?? '').trim().replace('_', '-').toLowerCase();
  if (!raw) return fallback;
  if (raw === 'en' || raw.startsWith('en-')) return 'en';
  if (SIMPLIFIED_LOCALES.has(raw)) return 'zh-Hans';
  if (TRADITIONAL_LOCALES.has(raw)) return 'zh';
  if (raw === 'zh-hans' || raw.startsWith('zh-hans-')) return 'zh-Hans';
  if (raw === 'zh-hant' || raw.startsWith('zh-hant-')) return 'zh';
  if (raw === 'zh' || raw.startsWith('zh-')) return 'zh';
  return fallback;
}

/**
 * @param {unknown} locale
 * @returns {UiLang}
 */
export function detectUiLang(locale = globalThis.navigator?.language) {
  const raw = String(locale ?? '').trim();
  if (!raw) return 'en';
  return normalizeUiLang(raw, 'en');
}

/**
 * Catalogs use `zhHans` for the generated Simplified Chinese branch.
 *
 * @template T
 * @param {{ zh?: T, zhHans?: T, en?: T }} catalog
 * @param {UiLang | string} lang
 * @returns {T}
 */
export function selectUiCatalog(catalog, lang) {
  const normalized = normalizeUiLang(lang);
  const key = normalized === 'zh-Hans' ? 'zhHans' : normalized;
  return catalog[key] ?? catalog.zh ?? catalog.en ?? catalog.zhHans;
}
