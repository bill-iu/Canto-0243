/**
 * PWA process-level relation graph (syn adjacency) — ADR-0023 § 關係圖快取 / dual-open.
 * Lazy build on first derived_ant / mirror use; invalidate when lexicon DB identity changes.
 */
import { queryRows } from './database-backend.ts';
import type { Database } from './sqljs.ts';
import { getStaticSynonyms } from './thesaurus.ts';

/** char → syn neighbors */
let adjacency: Map<string, Set<string>> = new Map();
let builtForDb: Database | null = null;
let buildPromise: Promise<void> | null = null;
/** Bumps on invalidate to cancel in-flight builds. */
let buildGeneration = 0;
/** Successful completed builds (for dual-open rebuild-once asserts). */
let completedBuilds = 0;
let lastMembershipSize = -1;
let graphReady = false;

function resetState(): void {
  adjacency = new Map();
  builtForDb = null;
  buildPromise = null;
  lastMembershipSize = -1;
  graphReady = false;
}

/** Call when lexicon DB is closed / replaced. */
export function invalidateRelationGraph(): void {
  buildGeneration += 1;
  resetState();
}

export function isRelationGraphReady(db: Database): boolean {
  return graphReady && builtForDb === db;
}

/** Number of successful graph builds since process start (not cleared by invalidate). */
export function relationGraphBuildCount(): number {
  return completedBuilds;
}

function addEdge(adj: Map<string, Set<string>>, a: string, b: string): void {
  if (!a || !b || a === b) return;
  let sa = adj.get(a);
  if (!sa) {
    sa = new Set();
    adj.set(a, sa);
  }
  sa.add(b);
  let sb = adj.get(b);
  if (!sb) {
    sb = new Set();
    adj.set(b, sb);
  }
  sb.add(a);
}

async function buildGraph(
  db: Database,
  membership: Set<string> | null,
  includeStatic: boolean,
  generation: number,
): Promise<void> {
  const rows = await queryRows(
    db,
    `
    SELECT w1.char AS a, w2.char AS b
    FROM words w1
    JOIN word_relations wr ON wr.word_id = w1.id
    JOIN words w2 ON w2.id = wr.related_id
    WHERE wr.relation_type = 'syn' AND w1.char != w2.char
  `,
    [],
  );
  if (generation !== buildGeneration) {
    return;
  }

  const adj = new Map<string, Set<string>>();
  for (const row of rows) {
    const a = String(row.a ?? '');
    const b = String(row.b ?? '');
    addEdge(adj, a, b);
  }

  if (includeStatic && membership?.size) {
    for (const ch of membership) {
      for (const syn of getStaticSynonyms(ch)) {
        if (!syn || syn === ch || !membership.has(syn)) {
          continue;
        }
        addEdge(adj, ch, syn);
      }
    }
  }

  if (generation !== buildGeneration) {
    return;
  }
  adjacency = adj;
  builtForDb = db;
  lastMembershipSize = membership?.size ?? 0;
  graphReady = true;
  completedBuilds += 1;
}

/**
 * Lazy ensure process-level syn adjacency for this Database.
 * Dual consumers (近反義 pool + `!` ant path) share one open.
 */
export async function ensureRelationGraph(
  db: Database,
  membership: Set<string> | null = null,
  includeStatic = true,
): Promise<void> {
  const memSize = membership?.size ?? 0;
  if (
    graphReady &&
    builtForDb === db &&
    (!includeStatic || memSize === lastMembershipSize || memSize === 0)
  ) {
    return;
  }
  if (builtForDb !== db) {
    adjacency = new Map();
    builtForDb = null;
    lastMembershipSize = -1;
    graphReady = false;
  }
  if (!buildPromise) {
    const generation = buildGeneration;
    buildPromise = buildGraph(db, membership, includeStatic, generation).finally(() => {
      buildPromise = null;
    });
  }
  await buildPromise;
}

/** Direct syn neighbors from the cached graph (empty if not ready). */
export function directSynNeighbors(char: string): string[] {
  const ch = (char || '').trim();
  if (!ch) {
    return [];
  }
  return [...(adjacency.get(ch) ?? [])];
}

/** Snapshot of adjacency for tests / debug. */
export function relationGraphEdgeCount(): number {
  let n = 0;
  for (const set of adjacency.values()) {
    n += set.size;
  }
  return n >> 1;
}
