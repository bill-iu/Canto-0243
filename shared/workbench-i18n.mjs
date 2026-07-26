import { selectUiCatalog } from './ui-locale.mjs';

const WORKBENCH_COPY = {
  zh: {
    returnToSearch: '返回搜尋首頁',
    filtering: '正篩選候選',
    filterCountHidden: '啟用篩選時不顯示未篩選候選數。',
  },
  zhHans: {
    returnToSearch: '返回搜索首页',
    filtering: '正在筛选候选',
    filterCountHidden: '启用筛选时不显示未筛选候选数。',
  },
  en: {
    returnToSearch: 'Back to search home',
    filtering: 'Filtering candidates',
    filterCountHidden: 'Candidate count is hidden while filters are active.',
  },
};

export function getWorkbenchCopy(lang = 'zh') {
  return selectUiCatalog(WORKBENCH_COPY, lang);
}

export function workbenchI18nSelfCheck() {
  if (getWorkbenchCopy('zh').filtering !== '正篩選候選') throw new Error('workbench zh');
  if (getWorkbenchCopy('zh-Hans').filtering !== '正在筛选候选') throw new Error('workbench zh-Hans');
  if (getWorkbenchCopy('en').filtering !== 'Filtering candidates') throw new Error('workbench en');
}
