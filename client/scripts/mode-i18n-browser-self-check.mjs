/** ponytail: ensure mode-i18n loads without Node process global (browser bundle path) */
const saved = globalThis.process;
// @ts-expect-error simulate browser
delete globalThis.process;
try {
  const { getModeMeta, modeRedirectHint } = await import('../../shared/mode-i18n.mjs');
  if (getModeMeta('m1').readout !== '0243模式（鬆）') throw new Error('zh m1');
  if (!modeRedirectHint('m2', 'en').includes('02493 Mode (Strict)')) throw new Error('en hint');
  console.log('mode-i18n-browser-self-check: ok');
} finally {
  if (saved !== undefined) globalThis.process = saved;
}