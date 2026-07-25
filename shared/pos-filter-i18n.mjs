import { selectUiCatalog } from './ui-locale.mjs';

const POS_FILTER_COPY = {
  zh: {
    label: '詞性篩選',
    shortLabel: '詞性',
    close: '關閉',
    closeFilters: '關閉篩選',
    heading: '篩選結果',
    withinAcross: '同軸任一符合 · 跨軸全部符合',
    reset: '重設',
    axes: {
      pos: { title: '詞類', choices: { n: '名詞', v: '動詞', a: '形容詞', r: '副詞', x: '虛詞' } },
      family: { title: '語彙族', choices: { idiom: '熟語（全部）', chengyu: '成語', suyu: '俗語', yanyu: '諺語', xiehouyu: '歇後語' } },
      voice: { title: '語態', choices: { active: '主動式', passive: '被動式' } },
    },
  },
  zhHans: {
    label: '词性筛选',
    shortLabel: '词性',
    close: '关闭',
    closeFilters: '关闭筛选',
    heading: '筛选结果',
    withinAcross: '同轴任一符合 · 跨轴全部符合',
    reset: '重设',
    axes: {
      pos: { title: '词类', choices: { n: '名词', v: '动词', a: '形容词', r: '副词', x: '虚词' } },
      family: { title: '词汇族', choices: { idiom: '熟语（全部）', chengyu: '成语', suyu: '俗语', yanyu: '谚语', xiehouyu: '歇后语' } },
      voice: { title: '语态', choices: { active: '主动式', passive: '被动式' } },
    },
  },
  en: {
    label: 'Part-of-speech filters',
    shortLabel: 'POS',
    close: 'Close',
    closeFilters: 'Close filters',
    heading: 'FILTER RESULTS',
    withinAcross: 'Within axis: OR · Across axes: AND',
    reset: 'Reset',
    axes: {
      pos: { title: 'Word class', choices: { n: 'Noun', v: 'Verb', a: 'Adjective', r: 'Adverb', x: 'Function word' } },
      family: { title: 'Lexical family', choices: { idiom: 'Idiom (all)', chengyu: 'Chengyu', suyu: 'Colloquial saying', yanyu: 'Proverb', xiehouyu: 'Two-part allegorical saying' } },
      voice: { title: 'Voice', choices: { active: 'Active', passive: 'Passive' } },
    },
  },
};

export function getPosFilterCopy(lang = 'zh') {
  return selectUiCatalog(POS_FILTER_COPY, lang);
}

export function posFilterI18nSelfCheck() {
  if (getPosFilterCopy('zh').label !== '詞性篩選') throw new Error('pos filter zh');
  if (getPosFilterCopy('zh-Hans').axes.pos.choices.n !== '名词') throw new Error('pos filter zh-Hans');
  if (getPosFilterCopy('en').reset !== 'Reset') throw new Error('pos filter en');
}
