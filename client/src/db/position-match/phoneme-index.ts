/**
 * PWA runtime phoneme inverted index (final/initial only) — grill P1.
 * Lazy build on first use; invalidate when lexicon DB identity changes.
 */
import { queryRows } from '../database-backend.ts';
import type { Database } from '../sqljs.ts';
import { anchorPhonemeOptions } from './filters/f2-phoneme-anchor.ts';
import { getRhymeFinals, getWordParts, type WordRow } from './word-row.ts';

type Constraint = 'final' | 'initial';

/** length → rows (stable index into this array) */
let lengthBuckets: Map<number, WordRow[]> = new Map();
/** `${length}\0${pos}\0${phoneme}` → row indices in length bucket */
let finalIndex: Map<string, number[]> = new Map();
let initialIndex: Map<string, number[]> = new Map();
let builtForDb: Database | null = null;
let buildPromise: Promise<void> | null = null;
/** DB identity the in-flight build targets (avoid await wrong rebuild). */
let buildingForDb: Database | null = null;
let buildGeneration = 0;
const ENSURE_MAX_ATTEMPTS = 3;

function phonemeKey(length: number, pos: number, phoneme: string): string {
  return `${length}\0${pos}\0${phoneme}`;
}

function resetState(): void {
  lengthBuckets = new Map();
  finalIndex = new Map();
  initialIndex = new Map();
  builtForDb = null;
  buildPromise = null;
  buildingForDb = null;
}

/** Call when lexicon DB is closed / replaced. */
export function invalidatePhonemeIndex(): void {
  buildGeneration += 1;
  resetState();
}

export function isPhonemeIndexReady(db: Database): boolean {
  return builtForDb === db && lengthBuckets.size > 0;
}

export function phonemeIndexBuildCount(): number {
  return buildGeneration;
}

/** Yield so badge / input stay responsive during large builds (tail prewarm). */
function yieldToMain(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const BUILD_YIELD_EVERY = 2500;

async function buildIndex(db: Database, generation: number): Promise<void> {
  const rows = await queryRows(
    db,
    `SELECT char, jyutping, code, initials, finals, length FROM words`,
    [],
  );
  if (generation !== buildGeneration) {
    return;
  }

  const buckets = new Map<number, WordRow[]>();
  const finals = new Map<string, number[]>();
  const initials = new Map<string, number[]>();

  let n = 0;
  for (const raw of rows) {
    const row = raw as WordRow;
    const char = String(row.char ?? '');
    if (!char) continue;
    let length = Number(row.length ?? 0);
    if (!(length > 0)) {
      length = char.length;
    }
    if (!(length > 0)) continue;

    const entry: WordRow = {
      char,
      jyutping: String(row.jyutping ?? ''),
      code: String(row.code ?? ''),
      initials: row.initials,
      finals: row.finals,
      length,
    };

    let bucket = buckets.get(length);
    if (!bucket) {
      bucket = [];
      buckets.set(length, bucket);
    }
    const idx = bucket.length;
    bucket.push(entry);

    const finalParts = getRhymeFinals(entry);
    for (let pos = 0; pos < finalParts.length; pos++) {
      const ph = finalParts[pos];
      if (!ph) continue;
      const key = phonemeKey(length, pos, ph);
      const list = finals.get(key) ?? [];
      list.push(idx);
      finals.set(key, list);
    }
    const initParts = getWordParts(entry, 'initials');
    for (let pos = 0; pos < initParts.length; pos++) {
      const ph = initParts[pos];
      if (!ph) continue;
      const key = phonemeKey(length, pos, ph);
      const list = initials.get(key) ?? [];
      list.push(idx);
      initials.set(key, list);
    }

    n += 1;
    if (n % BUILD_YIELD_EVERY === 0) {
      if (generation !== buildGeneration) {
        return;
      }
      await yieldToMain();
    }
  }

  if (generation !== buildGeneration) {
    return;
  }
  lengthBuckets = buckets;
  finalIndex = finals;
  initialIndex = initials;
  builtForDb = db;
}

/** Lazy ensure index for this Database instance. Retry if invalidate cancelled build. */
export async function ensurePhonemeIndex(db: Database): Promise<void> {
  for (let attempt = 0; attempt < ENSURE_MAX_ATTEMPTS; attempt++) {
    if (builtForDb === db && lengthBuckets.size > 0) {
      return;
    }

    if (buildPromise && buildingForDb === db) {
      await buildPromise;
      if (builtForDb === db && lengthBuckets.size > 0) {
        return;
      }
      continue;
    }

    if (buildPromise && buildingForDb !== db) {
      await buildPromise;
      if (builtForDb === db && lengthBuckets.size > 0) {
        return;
      }
    }

    if (builtForDb !== db) {
      lengthBuckets = new Map();
      finalIndex = new Map();
      initialIndex = new Map();
      builtForDb = null;
    }

    if (builtForDb === db && lengthBuckets.size > 0) {
      return;
    }

    const generation = buildGeneration;
    buildingForDb = db;
    buildPromise = buildIndex(db, generation).finally(() => {
      buildPromise = null;
      buildingForDb = null;
    });
    await buildPromise;
  }
}

/**
 * Candidates for length/pos matching any phoneme in options.
 * Returns null if index not usable (caller should fall back to SQL unlimited).
 */
export async function getPhonemeIndexCandidates(
  db: Database,
  length: number,
  pos: number,
  phonemeOptions: ReadonlySet<string>,
  constraint: Constraint,
): Promise<WordRow[] | null> {
  if (!phonemeOptions.size || !length || pos < 0) {
    return [];
  }
  await ensurePhonemeIndex(db);
  if (builtForDb !== db) {
    return null;
  }
  const bucket = lengthBuckets.get(length);
  if (!bucket?.length) {
    return [];
  }
  const indexMap = constraint === 'final' ? finalIndex : initialIndex;
  const allowed = new Set<number>();
  for (const opt of phonemeOptions) {
    if (!opt) continue;
    const hits = indexMap.get(phonemeKey(length, pos, opt));
    if (!hits) continue;
    for (const i of hits) {
      allowed.add(i);
    }
  }
  return [...allowed]
    .sort((a, b) => a - b)
    .map((i) => bucket[i]!)
    .filter(Boolean);
}

/**
 * Resolve anchor char → phoneme options → inverted-index candidates.
 * Port of RhymeAnchorCandidateSource short-circuit.
 */
export async function getPhonemeAnchorCandidates(
  db: Database,
  length: number,
  pos: number,
  anchorChar: string,
  constraint: Constraint,
): Promise<WordRow[] | null> {
  if (!anchorChar || length <= 0 || pos < 0) {
    return [];
  }
  const options = await anchorPhonemeOptions(db, anchorChar, constraint);
  if (!options.size) {
    return [];
  }
  return getPhonemeIndexCandidates(db, length, pos, options, constraint);
}
