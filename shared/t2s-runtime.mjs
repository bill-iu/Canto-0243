/** Runtime t2s (Traditional → Simplified) for headword display. */
import charMap from './t2s-char-map.mjs';

/** Convert a string from Traditional Chinese to Simplified Chinese. */
export function toSimplified(text) {
  let out = '';
  for (const char of text) {
    out += charMap[char] ?? char;
  }
  return out;
}

export function t2sSelfCheck() {
  if (toSimplified('羣') !== '群') throw new Error('t2sSelfCheck: 羣→群');
  if (toSimplified('體') !== '体') throw new Error('t2sSelfCheck: 體→体');
  if (toSimplified('冇') !== '冇') throw new Error('t2sSelfCheck: 冇 unchanged');
  if (toSimplified('粵') !== '粤') throw new Error('t2sSelfCheck: 粵→粤');
  if (toSimplified('嘅') !== '嘅') throw new Error('t2sSelfCheck: 嘅 unchanged');
  console.log('t2s-runtime self-check: ok');
}

if (typeof process !== 'undefined' && import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}`) {
  t2sSelfCheck();
}
