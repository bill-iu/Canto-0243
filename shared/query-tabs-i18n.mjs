import { selectUiCatalog } from './ui-locale.mjs';

const TAB_COPY = {
  zh: {
    workbench: '句格工作台',
    guide: '搜尋教學',
    about: '關於 Canto-0243',
    relation: '補關係',
    corrections: '詞庫勘誤',
    newQuery: '新查詢',
  },
  zhHans: {
    workbench: '句格工作台',
    guide: '搜索教学',
    about: '关于 Canto-0243',
    relation: '补关系',
    corrections: '词库勘误',
    newQuery: '新查询',
  },
  en: {
    workbench: 'VerseCraft Workbench',
    guide: 'Search Guide',
    about: 'About Canto-0243',
    relation: 'Add relations',
    corrections: 'Lexicon corrections',
    newQuery: 'New query',
  },
};

export function getQueryTabCopy(lang = 'zh') {
  return selectUiCatalog(TAB_COPY, lang);
}

export function queryTabsI18nSelfCheck() {
  if (getQueryTabCopy('zh').guide !== '搜尋教學') throw new Error('query tabs zh');
  if (getQueryTabCopy('zh-Hans').guide !== '搜索教学') throw new Error('query tabs zh-Hans');
  if (getQueryTabCopy('en').newQuery !== 'New query') throw new Error('query tabs en');
}
