import { selectUiCatalog } from './ui-locale.mjs';

const PORTABLE_UPDATE_COPY = {
  zh: {
    title: (tag) => `有新正式版${tag ? `：${tag}` : ''}`,
    sub: '請下載完整套件，關閉本程式後解壓覆蓋舊資料夾。',
    open: '前往 Release',
    copy: '複製下載指令',
    later: '稍後',
  },
  zhHans: {
    title: (tag) => `有新正式版${tag ? `：${tag}` : ''}`,
    sub: '请下载完整套件，关闭本程式后解压覆盖旧资料夹。',
    open: '前往 Release',
    copy: '复制下载指令',
    later: '稍后',
  },
  en: {
    title: (tag) => `Update available${tag ? `: ${tag}` : ''}`,
    sub: 'Download the full package, close this app, then extract over the old folder.',
    open: 'Open Release',
    copy: 'Copy download cmd',
    later: 'Later',
  },
};

export function getPortableUpdateCopy(lang = 'zh') {
  return selectUiCatalog(PORTABLE_UPDATE_COPY, lang);
}

export function portableUpdateI18nSelfCheck() {
  if (getPortableUpdateCopy('zh').title('v1') !== '有新正式版：v1') throw new Error('portable update zh');
  if (getPortableUpdateCopy('zh-Hans').copy !== '复制下载指令') throw new Error('portable update zh-Hans');
  if (getPortableUpdateCopy('en').later !== 'Later') throw new Error('portable update en');
}
