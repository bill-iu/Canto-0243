/** Query normalize — port of query_lexer bits used by parse. */
import { defaultSyllableLettersForAnchorChar } from '../../rime-index.ts';

/** Port of query_lexer.normalize_code_sandwich_tail_equals (ADR-0028) */
function normalizeCodeSandwichTailEquals(q: string): string {
  if (!q || q.includes('=')) {
    return q;
  }
  if (/^(\d+)([\u4e00-\u9fff]+)$/.test(q)) {
    return `${q}=`;
  }
  return q;
}

/** Port of jyutping_anchor.normalize_hanzi_dollar_syllable_anchors */
function normalizeHanziDollarSyllableAnchors(q: string): string {
  if (!q || !q.includes('$')) {
    return q;
  }
  const out: string[] = [];
  let i = 0;
  while (i < q.length) {
    if (q[i] === '$') {
      let j = i;
      while (j < q.length && q[j] === '$') {
        j += 1;
      }
      if (j - i >= 2) {
        out.push(q.slice(i, j));
        i = j;
        continue;
      }
    }
    if (
      q[i] === '$' &&
      i + 1 < q.length &&
      /^[\u4e00-\u9fff]$/.test(q[i + 1]!)
    ) {
      const letters = defaultSyllableLettersForAnchorChar(q[i + 1]!);
      if (letters) {
        out.push(letters);
        i += 2;
        continue;
      }
    }
    out.push(q[i]!);
    i += 1;
  }
  return out.join('');
}

export function normalizeQuery(q: string): string {
  if (!q) return q;
  
  // Strip whitespace
  let normalized = q.trim();
  
  // Convert full-width punctuation to half-width
  // Full-width: ！＠＃＄％＆＊（）＋－＝７８？、。
  // Half-width: !@#$%&*()+-=78?,.
  const fullToHalf: Record<string, string> = {
    '！': '!', '＠': '@', '＃': '#', '＄': '$', '％': '%',
    '＆': '&', '＊': '*', '（': '(', '）': ')', '＋': '+',
    '－': '-', '＝': '=', '７': '7', '８': '8', '？': '?',
    '、': ',', '。': '.',
  };
  
  normalized = normalized.replace(/[！＠＃＄％＆＊（）＋－＝７８？、。]/g, (match) => fullToHalf[match] || match);
  normalized = normalized.replace(/～～/g, '~~').replace(/！！/g, '!!');

  normalized = normalizeHanziDollarSyllableAnchors(normalized);
  return normalizeCodeSandwichTailEquals(normalized);
}

export function isPureDigits(q: string): boolean {
  return /^\d+$/.test(q);
}

/** Check if query contains Chinese characters */
export function hasChineseChars(q: string): boolean {
  return /[\u4e00-\u9fff]/.test(q);
}

/** Check if query looks like jyutping (contains letters) */
export function hasJyutpingChars(q: string): boolean {
  return /[a-zA-Z]/.test(q);
}
