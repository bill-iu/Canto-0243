import { selectUiCatalog } from './ui-locale.mjs';

const MODE_MENU_COPY = {
  zh: {
    groups: {
      searchModes: '搜尋模式',
      featurePages: '功能頁',
      tools: '工具',
      display: '顯示',
      textSize: '字體大小',
    },
    workbench: { title: '句格工作台', help: '逐格掌握聲調、押韻與原意' },
    guide: { title: '搜尋教學', help: '完整語法與例子' },
    relation: { title: '補關係', help: '為已收錄字面補近義或反義' },
    about: { title: '關於', help: '授權、致謝與回報' },
    stopLocal: { title: '停止本機服務', help: '立即關閉本機查韻服務' },
    stopMode: {
      title: '關頁即停本機服務',
      on: '開：關閉最後分頁即停（刷新唔停）',
      off: '關：服務常駐，選單可手動停止',
    },
    displayControls: {
      theme: '切換主題',
      traditional: '繁體中文',
      simplified: '簡體中文',
      english: '英文',
    },
    entrySize: { small: '小', medium: '中', large: '大' },
    githubHelp: '專案主頁 · 源碼與發佈',
    lexiconPrefix: '詞庫版本：',
  },
  zhHans: {
    groups: {
      searchModes: '搜索模式',
      featurePages: '功能页',
      tools: '工具',
      display: '显示',
      textSize: '字体大小',
    },
    workbench: { title: '句格工作台', help: '逐格掌握声调、押韵与原意' },
    guide: { title: '搜索教学', help: '完整语法与例子' },
    relation: { title: '补关系', help: '为已收录字面补近义或反义' },
    about: { title: '关于', help: '授权、致谢与回报' },
    stopLocal: { title: '停止本机服务', help: '立即关闭本机查韵服务' },
    stopMode: {
      title: '关页即停本机服务',
      on: '开：关闭最后分页即停（刷新不停）',
      off: '关：服务常驻，选单可手动停止',
    },
    displayControls: {
      theme: '切换主题',
      traditional: '繁体中文',
      simplified: '简体中文',
      english: '英文',
    },
    entrySize: { small: '小', medium: '中', large: '大' },
    githubHelp: '项目主页 · 源码与发布',
    lexiconPrefix: '词库版本：',
  },
  en: {
    groups: {
      searchModes: 'Search modes',
      featurePages: 'Feature pages',
      tools: 'Tools',
      display: 'Display',
      textSize: 'Text size',
    },
    workbench: { title: 'Line Workbench', help: 'Shape tone, rhyme and meaning slot by slot' },
    guide: { title: 'Search Guide', help: 'Full syntax & examples' },
    relation: { title: 'Add relations', help: 'Add synonym or antonym links' },
    about: { title: 'About', help: 'License, credits & feedback' },
    stopLocal: { title: 'Stop local service', help: 'Stop the local server now' },
    stopMode: {
      title: 'Stop when last tab closes',
      on: 'On: last tab closes stops server (reload safe)',
      off: 'Off: server stays up; use menu to stop',
    },
    displayControls: {
      theme: 'Toggle theme',
      traditional: 'Traditional Chinese',
      simplified: 'Simplified Chinese',
      english: 'English',
    },
    entrySize: { small: 'S', medium: 'M', large: 'L' },
    githubHelp: 'Project home · source & releases',
    lexiconPrefix: 'Lexicon version: ',
  },
};

export function getModeMenuCopy(lang = 'zh') {
  return selectUiCatalog(MODE_MENU_COPY, lang);
}

export function modeMenuI18nSelfCheck() {
  const zh = getModeMenuCopy('zh');
  const hans = getModeMenuCopy('zh-Hans');
  const en = getModeMenuCopy('en');
  if (zh.groups.searchModes !== '搜尋模式') throw new Error('mode menu zh');
  if (hans.groups.searchModes !== '搜索模式') throw new Error('mode menu zh-Hans');
  if (en.groups.searchModes !== 'Search modes') throw new Error('mode menu en');
  if (hans.stopMode.on === zh.stopMode.on) throw new Error('mode menu locale split');
  if (en.entrySize.small !== 'S') throw new Error('mode menu english size');
}
