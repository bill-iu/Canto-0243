import { selectUiCatalog } from './ui-locale.mjs';

const TAB_COPY = {
  zh: {
    queryTabs: '查詢分頁',
    chromeTabs: '查詢分頁列（Chrome Tabs）',
    dragToReorder: '拖曳以重排（桌面滑鼠；手機長按）',
    close: (label) => `關閉「${label}」`,
    workbench: '句格工作台',
    guide: '搜尋教學',
    about: '關於 Canto-0243',
    relation: '補關係',
    corrections: '詞庫勘誤',
    newQuery: '新查詢',
  },
  zhHans: {
    queryTabs: '查询分页',
    chromeTabs: '查询分页列（Chrome Tabs）',
    dragToReorder: '拖曳以重排（桌面鼠标；手机长按）',
    close: (label) => `关闭「${label}」`,
    workbench: '句格工作台',
    guide: '搜索教学',
    about: '关于 Canto-0243',
    relation: '补关系',
    corrections: '词库勘误',
    newQuery: '新查询',
  },
  en: {
    queryTabs: 'Query tabs',
    chromeTabs: 'Chrome tabs strip',
    dragToReorder: 'Drag to reorder (desktop mouse; long-press on mobile)',
    close: (label) => `Close “${label}”`,
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
  if (getQueryTabCopy('zh-Hans').queryTabs !== '查询分页') throw new Error('query tabs chrome zh-Hans');
  if (getQueryTabCopy('en').close('x') !== 'Close “x”') throw new Error('query tabs close en');
}
