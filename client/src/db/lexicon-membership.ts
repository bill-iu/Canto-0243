/**
 * Process-level DISTINCT char membership for 近反義 derived-ant.
 * loadDbCharSet full-table scan is the hot cost on every ~ / ! pool build — cache once per DB.
 */
import { queryRows } from './database-backend.ts';
import type { Database } from './sqljs.ts';

let cached: Set<string> | null = null;
let cachedForDb: Database | null = null;
let buildPromise: Promise<Set<string>> | null = null;
let buildingForDb: Database | null = null;

export function invalidateLexiconMembership(): void {
  cached = null;
  cachedForDb = null;
  buildPromise = null;
  buildingForDb = null;
}

export function isLexiconMembershipReady(db: Database): boolean {
  return cachedForDb === db && cached != null && cached.size > 0;
}

async function loadDistinctChars(db: Database): Promise<Set<string>> {
  const rows = await queryRows(db, 'SELECT DISTINCT char FROM words');
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String((row as { char?: string }).char ?? '');
    if (ch) out.add(ch);
  }
  return out;
}

/** Cached DISTINCT words.char set for this Database identity. */
export async function getLexiconMembership(db: Database): Promise<Set<string>> {
  if (cachedForDb === db && cached) {
    return cached;
  }
  if (buildPromise && buildingForDb === db) {
    return buildPromise;
  }
  buildingForDb = db;
  buildPromise = loadDistinctChars(db)
    .then((set) => {
      cached = set;
      cachedForDb = db;
      return set;
    })
    .finally(() => {
      buildPromise = null;
      buildingForDb = null;
    });
  return buildPromise;
}

/** Alias for tail stage — await getLexiconMembership (no fire-and-forget). */
export async function prewarmLexiconMembership(db: Database): Promise<void> {
  await getLexiconMembership(db);
}
