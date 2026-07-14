/**
 * 標準詞條列表統計文案（PWA／Portable 共用）。
 * 「結果」＝合併後字面數，唔係讀音擷取列數。
 */

/** @param {number} mergedCount @param {boolean} hasMore */
export function formatStandardResultCountLabel(mergedCount, hasMore) {
  const n = Math.max(0, Number(mergedCount) || 0);
  if (n <= 0) return '';
  if (hasMore) return `已載入 ${n} 個結果`;
  return `${n} 個結果`;
}

/** ponytail: `node frontend/scripts/result-stats-self-check.mjs` */
export function resultStatsSelfCheck() {
  if (formatStandardResultCountLabel(25, false) !== '25 個結果') {
    throw new Error('result-stats: complete');
  }
  if (formatStandardResultCountLabel(25, true) !== '已載入 25 個結果') {
    throw new Error('result-stats: hasMore');
  }
  if (formatStandardResultCountLabel(0, true) !== '') {
    throw new Error('result-stats: empty');
  }
}
