/** Word row helpers — port of word_serializer subset for position-match */

import { decodePhonemeField } from '../phoneme-codec.ts';

export type WordRow = Record<string, unknown>;

export function getWordText(row: WordRow): string {
  return String(row.char ?? '');
}

export function getWordCode(row: WordRow): string {
  return String(row.code ?? '');
}

export function getWordParts(row: WordRow, field: 'initials' | 'finals'): string[] {
  const dim = field === 'finals' ? 'final' : 'initial';
  return decodePhonemeField(row[field], dim);
}

export function getRhymeFinals(row: WordRow): string[] {
  return getWordParts(row, 'finals');
}
