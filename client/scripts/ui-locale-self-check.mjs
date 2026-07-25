/** Candidate 01: locale normalization and catalog selection seam. */
import assert from 'node:assert/strict';
import {
  detectUiLang,
  normalizeUiLang,
  selectUiCatalog,
} from '../../shared/ui-locale.mjs';

assert.equal(normalizeUiLang('zh-Hans'), 'zh-Hans');
assert.equal(normalizeUiLang('zh-CN'), 'zh-Hans');
assert.equal(normalizeUiLang('zh-SG'), 'zh-Hans');
assert.equal(normalizeUiLang('zh-Hant'), 'zh');
assert.equal(normalizeUiLang('zh-HK'), 'zh');
assert.equal(normalizeUiLang('zh-TW'), 'zh');
assert.equal(normalizeUiLang('zh'), 'zh');
assert.equal(normalizeUiLang('en-US'), 'en');
assert.equal(normalizeUiLang('fr-FR'), 'zh');

assert.equal(detectUiLang('zh-CN'), 'zh-Hans');
assert.equal(detectUiLang('zh-HK'), 'zh');
assert.equal(detectUiLang('zh'), 'zh');
assert.equal(detectUiLang('en-US'), 'en');
assert.equal(detectUiLang(''), 'en');

const catalog = {
  zh: { title: '繁' },
  zhHans: { title: '简' },
  en: { title: 'EN' },
};
assert.equal(selectUiCatalog(catalog, 'zh').title, '繁');
assert.equal(selectUiCatalog(catalog, 'zh-Hans').title, '简');
assert.equal(selectUiCatalog(catalog, 'en').title, 'EN');
assert.equal(selectUiCatalog({ zh: { title: '繁' } }, 'zh-Hans').title, '繁');

console.log('ui-locale-self-check: ok');
