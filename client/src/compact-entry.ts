export type CompactEntryLength = 'short' | 'medium' | 'long' | 'overflow';

export function compactEntryLength(literal: string): CompactEntryLength {
  const length = [...literal].length;
  if (length <= 3) return 'short';
  if (length === 4) return 'medium';
  if (length === 5) return 'long';
  return 'overflow';
}

export function compactEntrySelfCheck(): void {
  const cases: Array<[string, CompactEntryLength]> = [
    ['', 'short'],
    ['香港', 'short'],
    ['一二三四', 'medium'],
    ['一二三四五', 'long'],
    ['一二三四五六', 'overflow'],
  ];
  for (const [literal, expected] of cases) {
    const actual = compactEntryLength(literal);
    if (actual !== expected) {
      throw new Error(`compactEntrySelfCheck: ${literal || '(empty)'} → ${actual}, want ${expected}`);
    }
  }
}
