/**
 * 標準詞條列表統計文案（PWA／Portable 共用）。
 * 「結果」＝合併後字面總數（引擎 total），唔係讀音擷取列數／已載入批次數。
 */

/** @param {number | null | undefined} literalTotal */
export function formatStandardResultCountLabel(literalTotal, lang = 'zh') {
  if (literalTotal == null) return '';
  const n = Math.max(0, Number(literalTotal) || 0);
  if (n <= 0) return '';
  return getResultStatsCopy(lang).standard(n);
}

/** ponytail: `node shared/scripts/result-stats-self-check.mjs` */
export function resultStatsSelfCheck() {
  if (formatStandardResultCountLabel(2825) !== '搜到 2825 個結果') {
    throw new Error('result-stats: total');
  }
  if (formatStandardResultCountLabel(0) !== '') {
    throw new Error('result-stats: zero');
  }
  if (formatStandardResultCountLabel(null) !== '') {
    throw new Error('result-stats: null');
  }
  if (formatStandardResultCountLabel(undefined) !== '') {
    throw new Error('result-stats: undefined');
  }
}
import { getResultStatsCopy } from './result-stats-i18n.mjs';
