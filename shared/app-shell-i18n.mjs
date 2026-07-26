import { selectUiCatalog } from './ui-locale.mjs';

const APP_SHELL_COPY = {
  zh: {
    title: 'ONE·搵·韻',
    returnToSearch: '返回搜尋首頁',
    workbenchTitle: '句格工作台',
    workbenchSub: '聲調 · 押韻 · 原意',
    searchLabel: '搜尋內容',
    searchButton: '搜尋',
    shuffleResults: '隨機打亂結果',
    toneProfile: '聲調數字檔',
    searching: '搜尋中…',
    filteredResults: (count, loaded, suffix) => `篩選後 ${count} 項（已載入 ${loaded} 項）${suffix}`,
    noLoadedResults: '已載入結果中沒有符合這組篩選的項目。',
    loadingMore: '正繼續載入更多結果檢查⋯',
    resetFilter: '請重設或放寬篩選。',
  },
  zhHans: {
    title: 'ONE·揾·韵',
    returnToSearch: '返回搜索首页',
    workbenchTitle: '句格工作台',
    workbenchSub: '声调 · 押韵 · 原意',
    searchLabel: '搜索内容',
    searchButton: '搜索',
    shuffleResults: '随机打乱结果',
    toneProfile: '声调数字档',
    searching: '搜索中…',
    filteredResults: (count, loaded, suffix) => `筛选后 ${count} 项（已载入 ${loaded} 项）${suffix}`,
    noLoadedResults: '已载入结果中没有符合这组筛选的项目。',
    loadingMore: '正继续载入更多结果检查⋯',
    resetFilter: '请重设或放宽筛选。',
  },
  en: {
    title: 'WRITE·RIGHT·RHYME',
    returnToSearch: 'Back to search home',
    workbenchTitle: 'VerseCraft Workbench',
    workbenchSub: 'Tone · rhyme · sense',
    searchLabel: 'Search',
    searchButton: 'Search',
    shuffleResults: 'Shuffle results',
    toneProfile: 'Tone-digit profile',
    searching: 'Searching…',
    filteredResults: (count, loaded, suffix) => `${count} filtered (from ${loaded} loaded)${suffix}`,
    noLoadedResults: 'No loaded results match these filters.',
    loadingMore: 'Loading more results to continue checking…',
    resetFilter: 'Reset or loosen a filter.',
  },
};

export function getAppShellCopy(lang = 'zh') {
  return selectUiCatalog(APP_SHELL_COPY, lang);
}

export function appShellI18nSelfCheck() {
  if (getAppShellCopy('zh').searchButton !== '搜尋') throw new Error('app shell zh');
  if (getAppShellCopy('zh-Hans').searchButton !== '搜索') throw new Error('app shell zh-Hans');
  if (getAppShellCopy('en').filteredResults(2, 10, '') !== '2 filtered (from 10 loaded)') {
    throw new Error('app shell en');
  }
}
