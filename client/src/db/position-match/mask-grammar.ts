/** Port of app/services/query_grammar/mask.py */

const WILDCARD_CHARS = new Set(['?', '_', '%']);

export function isWildcardChar(ch: string): boolean {
  return WILDCARD_CHARS.has(ch);
}

export function parseMaskQuery(mask: string): {
  width: number;
  requiredCodes: Array<string | null>;
  literalPositions: Array<[number, string]>;
} {
  const requiredCodes: Array<string | null> = Array(mask.length).fill(null);
  const literalPositions: Array<[number, string]> = [];
  for (let idx = 0; idx < mask.length; idx++) {
    const ch = mask[idx]!;
    if (isWildcardChar(ch)) {
      continue;
    }
    if (/\d/.test(ch)) {
      requiredCodes[idx] = ch;
      continue;
    }
    literalPositions.push([idx, ch]);
  }
  return { width: mask.length, requiredCodes, literalPositions };
}

export function buildMaskFromSlots(slots: string, width: number, anchorPos: number): string {
  const chars = Array(width).fill('?');
  if (anchorPos === 0) {
    for (let i = 0; i < slots.length; i++) {
      chars[i + 1] = slots[i]!;
    }
  } else {
    for (let i = 0; i < slots.length; i++) {
      chars[i] = slots[i]!;
    }
  }
  return chars.join('');
}
