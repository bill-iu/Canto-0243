/** Word row helpers — port of word_serializer subset for position-match */

export type WordRow = Record<string, unknown>;

export function getWordText(row: WordRow): string {
  return String(row.char ?? '');
}

export function getWordCode(row: WordRow): string {
  return String(row.code ?? '');
}

function loadJsonList(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(String);
  }
  if (typeof raw === 'string' && raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  return [];
}

export function getWordParts(row: WordRow, field: 'initials' | 'finals'): string[] {
  return loadJsonList(row[field]);
}

export function getRhymeFinals(row: WordRow): string[] {
  return getWordParts(row, 'finals');
}
