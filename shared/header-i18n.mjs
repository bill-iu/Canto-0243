import { selectUiCatalog } from './ui-locale.mjs';

const HEADER_COPY = {
  zh: {
    title: 'ONE·搵·韻',
    tagline: '格律／協音／押韻／近反義，一步搵到。',
  },
  zhHans: {
    title: 'ONE·揾·韵',
    tagline: '格律／协音／押韵／近反义，一步揾到。',
  },
  en: {
    title: 'WRITE·RIGHT·RHYME',
    tagline: 'Meter / sound match / rhyme / near-antonyms — find in one step.',
  },
};

export function getHeaderCopy(lang = 'zh') {
  return selectUiCatalog(HEADER_COPY, lang);
}

export function headerI18nSelfCheck() {
  if (getHeaderCopy('zh').title !== 'ONE·搵·韻') throw new Error('header zh');
  if (getHeaderCopy('zh-Hans').title !== 'ONE·揾·韵') throw new Error('header zh-Hans');
  if (getHeaderCopy('en').title !== 'WRITE·RIGHT·RHYME') throw new Error('header en');
}
