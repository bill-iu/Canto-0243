import assert from 'node:assert/strict';

const values = new Map();
globalThis.localStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: (key) => values.delete(key),
};
Object.defineProperty(globalThis, 'navigator', { value: { language: 'zh-CN' }, configurable: true });
globalThis.document = {
  documentElement: { dataset: {} },
  querySelector: () => null,
  getElementById: () => null,
};
globalThis.window = { matchMedia: () => ({ matches: false }) };

const { getLang, setLang } = await import('../../shared/app-context.mjs');

assert.equal(getLang(), 'zh-Hans');
setLang('zh-Hans');
assert.equal(getLang(), 'zh-Hans');
setLang('en');
assert.equal(getLang(), 'en');
values.set('canto-lang', 'invalid');
assert.equal(getLang(), 'zh-Hans');

console.log('app-context-locale-self-check: ok');
