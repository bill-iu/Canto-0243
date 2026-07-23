import type { DatabaseBackend } from './database-backend.ts';
import { queryFirst } from './database-backend.ts';

export class LexiconLengthInvariantError extends Error {
  constructor() {
    super('lexicon contains an invalid words.length row');
    this.name = 'LexiconLengthInvariantError';
  }
}

export async function assertLexiconLengthInvariant(db: DatabaseBackend): Promise<void> {
  const invalid = await queryFirst(
    db,
    `SELECT 1
     FROM words
     WHERE length IS NULL OR length = 0 OR length != length(char)
     LIMIT 1`,
  );
  if (invalid) throw new LexiconLengthInvariantError();
}
