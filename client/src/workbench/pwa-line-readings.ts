import type { DatabaseBackend } from '../db/database-backend.ts';
import { queryRows } from '../db/database-backend.ts';
import { splitJyutping } from '../db/jyutping-codec.ts';
import { compareAuthoritativeReadings } from '../db/ranking.ts';

export interface PwaReadingRow {
  char: string;
  jyutping: string;
  code: string;
}

export interface PwaLineReadingChoice {
  jyutping: string;
  code: string;
  initial: string;
  final: string;
}

export interface PwaLineReadingSlot {
  surface: string;
  kind: 'resolved' | 'unresolved' | 'punctuation';
  choices: PwaLineReadingChoice[];
  needsChoice: boolean;
}

function isPunctuation(surface: string): boolean {
  return /^[\p{P}\p{Z}]$/u.test(surface);
}

function toChoice(row: PwaReadingRow): PwaLineReadingChoice {
  const [initials, finals] = splitJyutping(row.jyutping);
  return {
    jyutping: row.jyutping.trim(),
    code: row.code.trim(),
    initial: initials[0] ?? '',
    final: finals[0] ?? '',
  };
}

export function resolveLineReadingsFromRows(surface: string, rows: PwaReadingRow[]): PwaLineReadingSlot[] {
  const bySurface = new Map<string, PwaReadingRow[]>();
  for (const row of rows) {
    const bucket = bySurface.get(row.char) ?? [];
    bucket.push(row);
    bySurface.set(row.char, bucket);
  }

  return Array.from(surface, (literal) => {
    const ordered = [...(bySurface.get(literal) ?? [])].sort(compareAuthoritativeReadings);
    const choices: PwaLineReadingChoice[] = [];
    const seen = new Set<string>();
    for (const row of ordered) {
      const choice = toChoice(row);
      const key = JSON.stringify(choice);
      if (!choice.jyutping || seen.has(key)) continue;
      seen.add(key);
      choices.push(choice);
    }
    if (choices.length === 0) {
      return {
        surface: literal,
        kind: isPunctuation(literal) ? 'punctuation' : 'unresolved',
        choices: [],
        needsChoice: false,
      };
    }
    const material = new Set(choices.map((choice) => `${choice.code}\t${choice.initial}\t${choice.final}`));
    const needsChoice = material.size > 1;
    return {
      surface: literal,
      kind: 'resolved',
      choices: needsChoice ? choices : choices.slice(0, 1),
      needsChoice,
    };
  });
}

export async function resolvePwaLineReadings(
  surface: string,
  db: DatabaseBackend,
): Promise<PwaLineReadingSlot[]> {
  const literals = [...new Set(Array.from(surface).filter((value) => !isPunctuation(value)))];
  if (literals.length === 0) return resolveLineReadingsFromRows(surface, []);
  const placeholders = literals.map(() => '?').join(', ');
  const rows = await queryRows(
    db,
    `SELECT char, jyutping, code FROM words WHERE char IN (${placeholders})`,
    literals,
  );
  return resolveLineReadingsFromRows(surface, rows.map((row) => ({
    char: String(row.char ?? ''),
    jyutping: String(row.jyutping ?? ''),
    code: String(row.code ?? ''),
  })));
}
