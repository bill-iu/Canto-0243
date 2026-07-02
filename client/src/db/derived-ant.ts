/**
 * Runtime derived ant — port of derived_ant.py + cilin_derived + mirror_ant (subset)
 */
import type { Database } from './sqljs.ts';
import { getCilinSynonyms, getStaticAntonyms, getStaticSynonyms } from './thesaurus.ts';
import type { RelationPoolItem } from './relation-pool.ts';

const CJK_RE = /[\u4e00-\u9fff]/;

const DERIVED_ANT_SOURCES = new Set([
  'ant_syn_mirror',
  'ant_cilin_exanded',
  'ant_syn_bridge',
  'manual_ant_mirror',
]);

export const CILIN_DERIVED_SOURCE = 'ant_cilin_exanded';
export const CILIN_DERIVED_CONFIDENCE = 0.75;
export const MIRROR_SOURCE = 'ant_syn_mirror';
export const MIRROR_CONFIDENCE = 0.72;

function poolLiteral(text: string): string | null {
  const t = (text ?? '')
    .trim()
    .replace(/[（(].*?[）)]/g, '')
    .replace(/\s+/g, '');
  if (!t || t.length > 12 || !CJK_RE.test(t) || /[0-9A-Za-z_]/.test(t)) {
    return null;
  }
  return t;
}

function finalScore(source: string, confidence: number, inDb: boolean): number {
  const ranks: Record<string, number> = {
    guotong: 15,
    cilin: 10,
    ant_cilin_exanded: 25,
    ant_syn_mirror: 28,
    ant_syn_bridge: 28,
    runtime_static: 80,
    word_relations: 50,
  };
  let rank = 50;
  for (const [key, val] of Object.entries(ranks)) {
    if (source.includes(key)) {
      rank = val;
      break;
    }
  }
  return rank + confidence * 20 + (inDb ? 5 : -10);
}

function derivedAntItem(char: string, source: string, confidence: number, inDb: boolean): RelationPoolItem {
  return {
    char,
    relation: 'ant',
    source,
    score: confidence,
    in_db: inDb,
    jyutping: '',
    code: '',
    group_codes: [],
    _sort: finalScore(source, confidence, inDb),
  };
}

function loadDbSynAdjacency(db: Database, membership: Set<string>): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>();
  const stmt = db.prepare(`
    SELECT w1.char AS a, w2.char AS b
    FROM words w1
    JOIN word_relations wr ON wr.word_id = w1.id
    JOIN words w2 ON w2.id = wr.related_id
    WHERE wr.relation_type = 'syn' AND w1.char != w2.char
  `);
  while (stmt.step()) {
    const row = stmt.getAsObject() as Record<string, unknown>;
    const a = String(row.a ?? '');
    const b = String(row.b ?? '');
    if (!a || !b) {
      continue;
    }
    if (!adj.has(a)) {
      adj.set(a, new Set());
    }
    if (!adj.has(b)) {
      adj.set(b, new Set());
    }
    adj.get(a)!.add(b);
    adj.get(b)!.add(a);
  }
  stmt.free();
  if (membership) {
    for (const ch of membership) {
      for (const syn of getStaticSynonyms(ch)) {
        if (!syn || syn === ch || !membership.has(syn)) {
          continue;
        }
        if (!adj.has(ch)) {
          adj.set(ch, new Set());
        }
        if (!adj.has(syn)) {
          adj.set(syn, new Set());
        }
        adj.get(ch)!.add(syn);
        adj.get(syn)!.add(ch);
      }
    }
  }
  return adj;
}

function directSynNeighbors(
  adj: Map<string, Set<string>>,
  char: string,
): string[] {
  return [...(adj.get(char) ?? [])];
}

export function directAntSeedsForHead(
  db: Database,
  head: string,
  membership: Set<string>,
  includeStatic: boolean,
  relAntItems: Array<{ char: string; source: string }>,
): string[] {
  const q = head.trim();
  if (!q) {
    return [];
  }
  const seeds: string[] = [];
  const seen = new Set<string>([q]);
  for (const item of relAntItems) {
    if (DERIVED_ANT_SOURCES.has(item.source || '')) {
      continue;
    }
    const ch = poolLiteral(item.char);
    if (!ch || ch === q || !membership.has(ch) || seen.has(ch)) {
      continue;
    }
    seen.add(ch);
    seeds.push(ch);
  }
  if (includeStatic) {
    for (const ant of getStaticAntonyms(q)) {
      const ch = poolLiteral(ant);
      if (!ch || ch === q || !membership.has(ch) || seen.has(ch)) {
        continue;
      }
      seen.add(ch);
      seeds.push(ch);
    }
  }
  return seeds;
}

function cilinDerivedAntPairs(
  head: string,
  antSeeds: string[],
  membership: Set<string>,
): Array<[string, string]> {
  const h = head.trim();
  if (!h) {
    return [];
  }
  const out: Array<[string, string]> = [];
  const seenTails = new Set([h]);
  for (const seed of antSeeds) {
    const s = seed.trim();
    if (!s) {
      continue;
    }
    for (const syn of getCilinSynonyms(s)) {
      const tail = poolLiteral(syn);
      if (!tail || tail === h || seenTails.has(tail) || !membership.has(tail)) {
        continue;
      }
      seenTails.add(tail);
      out.push([h, tail]);
    }
  }
  return out;
}

function mirrorAntPairs(
  head: string,
  antSeeds: string[],
  synNeighborsOf: (seed: string) => string[],
  membership: Set<string>,
): Array<[string, string]> {
  const h = head.trim();
  if (!h) {
    return [];
  }
  const out: Array<[string, string]> = [];
  const seenTails = new Set([h]);
  for (const seed of antSeeds) {
    const s = seed.trim();
    if (!s) {
      continue;
    }
    for (const syn of synNeighborsOf(s)) {
      const tail = poolLiteral(syn);
      if (!tail || tail === h || seenTails.has(tail) || !membership.has(tail)) {
        continue;
      }
      seenTails.add(tail);
      out.push([h, tail]);
    }
  }
  return out;
}

export function appendRuntimeDerivedAntPool(
  query: string,
  antPool: RelationPoolItem[],
  db: Database,
  membership: Set<string>,
  includeStatic: boolean,
  morphemeChars: Set<string>,
  headSyns: Set<string>,
  relAntItems: Array<{ char: string; source: string }>,
): RelationPoolItem[] {
  const seeds = directAntSeedsForHead(db, query, membership, includeStatic, relAntItems);
  const present = membership;
  const merged = new Map(antPool.map((item) => [item.char, item]));

  for (const [, tail] of cilinDerivedAntPairs(query, seeds, present)) {
    if (!tail || headSyns.has(tail)) {
      continue;
    }
    const item = derivedAntItem(tail, CILIN_DERIVED_SOURCE, CILIN_DERIVED_CONFIDENCE, present.has(tail));
    const prev = merged.get(tail);
    if (!prev || item._sort < prev._sort) {
      merged.set(tail, item);
    }
  }

  const synAdj = loadDbSynAdjacency(db, membership);
  for (const [, tail] of mirrorAntPairs(query, seeds, (s) => directSynNeighbors(synAdj, s), present)) {
    if (!tail || headSyns.has(tail)) {
      continue;
    }
    const item = derivedAntItem(tail, MIRROR_SOURCE, MIRROR_CONFIDENCE, present.has(tail));
    const prev = merged.get(tail);
    if (!prev || item._sort < prev._sort) {
      merged.set(tail, item);
    }
  }

  return [...merged.values()];
}

/** ponytail: runnable self-check — `npx tsx client/scripts/derived-ant-self-check.ts` */
export function derivedAntLogicSelfCheck(db: Database): void {
  const membership = new Set(['快樂', '悲傷', '傷心', '哀愁']);
  const relAnt = [{ char: '悲傷', source: 'guotong' }];
  const seeds = directAntSeedsForHead(db, '快樂', membership, true, relAnt);
  if (!seeds.includes('悲傷')) {
    throw new Error('derivedAntLogicSelfCheck: seeds');
  }
  const cilinPairs = cilinDerivedAntPairs('快樂', seeds, membership);
  if (!cilinPairs.some(([, t]) => t === '傷心')) {
    throw new Error('derivedAntLogicSelfCheck: cilin');
  }
}
