import { selectUiCatalog } from './ui-locale.mjs';

const RESULT_STATS_COPY = {
  zh: {
    standard: (count) => `搜到 ${count} 個結果`,
    anchor: (initial, final, loaded, total) =>
      total != null && total > loaded
        ? `聲母 ${initial}　韻母 ${final}（已載入 ${loaded} / ${total}）`
        : `聲母 ${initial}　韻母 ${final}（已載入 ${loaded}）`,
    semantic: (syns, ants, related, loaded) =>
      `近義 ${syns}　反義 ${ants}${related > 0 ? `　語意相關 ${related}` : ''}（已載入 ${loaded}）`,
  },
  zhHans: {
    standard: (count) => `搜到 ${count} 个结果`,
    anchor: (initial, final, loaded, total) =>
      total != null && total > loaded
        ? `声母 ${initial}　韵母 ${final}（已载入 ${loaded} / ${total}）`
        : `声母 ${initial}　韵母 ${final}（已载入 ${loaded}）`,
    semantic: (syns, ants, related, loaded) =>
      `近义 ${syns}　反义 ${ants}${related > 0 ? `　语意相关 ${related}` : ''}（已载入 ${loaded}）`,
  },
  en: {
    standard: (count) => `${count} results`,
    anchor: (initial, final, loaded, total) =>
      total != null && total > loaded
        ? `Initial ${initial}　Final ${final} (${loaded} / ${total} loaded)`
        : `Initial ${initial}　Final ${final} (${loaded} loaded)`,
    semantic: (syns, ants, related, loaded) =>
      `Synonyms ${syns}　Antonyms ${ants}${related > 0 ? `　Related ${related}` : ''} (${loaded} loaded)`,
  },
};

export function getResultStatsCopy(lang = 'zh') {
  return selectUiCatalog(RESULT_STATS_COPY, lang);
}

export function resultStatsI18nSelfCheck() {
  if (getResultStatsCopy('zh').standard(2) !== '搜到 2 個結果') throw new Error('result stats zh');
  if (getResultStatsCopy('zh-Hans').standard(2) !== '搜到 2 个结果') throw new Error('result stats zh-Hans');
  if (getResultStatsCopy('en').standard(2) !== '2 results') throw new Error('result stats en');
}
