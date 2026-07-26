import { selectUiCatalog } from './ui-locale.mjs';

const WARMUP_COPY = {
  zh: { done: '完成！', loading: '載入中…' },
  zhHans: { done: '完成！', loading: '载入中…' },
  en: { done: 'Done!', loading: 'Loading…' },
};

export function getWarmupCopy(lang = 'zh') {
  return selectUiCatalog(WARMUP_COPY, lang);
}

export function warmupI18nSelfCheck() {
  if (getWarmupCopy('zh').loading !== '載入中…') throw new Error('warmup zh');
  if (getWarmupCopy('zh-Hans').loading !== '载入中…') throw new Error('warmup zh-Hans');
  if (getWarmupCopy('en').done !== 'Done!') throw new Error('warmup en');
}
