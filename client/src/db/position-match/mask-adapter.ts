/** Port of position_match/mask_adapter.py */
import { isWildcardChar } from './mask-grammar.ts';
import type { MatchSpec } from './spec.ts';

export function matchesMaskLiteralChars(wordChar: string, mask: string): boolean {
  if (wordChar.length !== mask.length) {
    return false;
  }
  for (let idx = 0; idx < mask.length; idx++) {
    const ch = mask[idx]!;
    if (isWildcardChar(ch) || /\d/.test(ch)) {
      continue;
    }
    if (wordChar[idx] !== ch) {
      return false;
    }
  }
  return true;
}

/** SQLite GLOB：通配／碼槽 → ?，字面保留 */
export function maskCharGlobPattern(mask: string): string {
  return [...mask]
    .map((ch) => (isWildcardChar(ch) || /\d/.test(ch) ? '?' : ch))
    .join('');
}

/** 首段連續字面（至第一個通配或碼槽） */
export function maskFixedLiteralPrefix(mask: string): string {
  const prefix: string[] = [];
  for (const ch of mask) {
    if (isWildcardChar(ch) || /\d/.test(ch)) {
      break;
    }
    prefix.push(ch);
  }
  return prefix.join('');
}

export function requiredCodesFromSpec(spec: MatchSpec): Array<string | null> {
  const codes: Array<string | null> = Array(spec.width).fill(null);
  const mask = spec.mask ?? '';
  if (mask.length === spec.width) {
    for (let idx = 0; idx < mask.length; idx++) {
      if (/\d/.test(mask[idx]!)) {
        codes[idx] = mask[idx]!;
      }
    }
  }
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'code_digit' && slot.pos >= 0 && slot.pos < spec.width && slot.value != null) {
      codes[slot.pos] = String(slot.value);
    }
  }
  return codes;
}
