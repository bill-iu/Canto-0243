/** 近反義池建構 — port of domain/relations/pool_builder.py (Phase C PR4). */
import type { Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import { getStaticAntonyms, getStaticSynonyms } from './thesaurus.ts';
import { getCuratedAntCompounds } from './compound.ts';
import { appendRuntimeDerivedAntPool } from './derived-ant.ts';
import {
  createRelationPoolSnapshot,
  type RelationKind,
  type RelationPoolItem,
  type RelationPoolSnapshot,
} from './relation-pool-snapshot.ts';
import {
  RUNTIME_DERIVED_ANT_SOURCES,
  finalScore,
  mergeRelationPools,
  morphemeCharsFromWordLists,
  sortAntPool,
  sortSynPool,
} from './relation-pool-ranking.ts';

const CJK_RE = /[\u4e00-\u9fff]/

export function poolLiteral(text: string): string | null {
  const t = (text ?? '')
    .trim()
    .replace(/[（(].*?[）)]/g, '')
    .replace(/\s+/g, '');
  if (!t || t.length > 12 || !CJK_RE.test(t) || /[0-9A-Za-z_]/.test(t)) {
    return null;
  }
  return t;
}
export function parseGroupCodes(raw: unknown): string[] {
  if (!raw) {
    return [];
  }
  if (Array.isArray(raw)) {
    return raw.map(String).filter(Boolean);
  }
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.map(String).filter(Boolean);
      }
    } catch {
      return raw ? [raw] : [];
    }
  }
  return [];
}

export function filterStaticWords(words: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const w of words) {
    const t = poolLiteral(w);
    if (t && !seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}
export async function charsPresentInDb(db: Database, chars: Iterable<string>): Promise<Set<string>> {
  const unique = [...new Set(chars)].filter(Boolean);
  if (!unique.length) {
    return new Set();
  }
  const present = new Set<string>();
  const chunk = 500;
  for (let i = 0; i < unique.length; i += chunk) {
    const part = unique.slice(i, i + chunk);
    const placeholders = part.map(() => '?').join(',');
    const rows = await queryRows(db, `SELECT DISTINCT char FROM words WHERE char IN (${placeholders})`, part);
    for (const row of rows) {
      const ch = String((row as { char?: string }).char ?? '');
      if (ch) {
        present.add(ch);
      }
    }
  }
  return present;
}

export async function loadDbCharSet(db: Database): Promise<Set<string>> {
  const rows = await queryRows(db, 'SELECT DISTINCT char FROM words');
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String((row as { char?: string }).char ?? '');
    if (ch) {
      out.add(ch);
    }
  }
  return out;
}

const BIDIRECTIONAL_REL_ROWS_SQL = `
  SELECT wr.relation_type AS relation_type, w2.char AS rchar, wr.source AS source,
         wr.score AS score, w2.jyutping AS jyutping, w2.code AS code, wr.group_codes AS group_codes
  FROM words w1
  JOIN word_relations wr ON wr.word_id = w1.id
  JOIN words w2 ON w2.id = wr.related_id
  WHERE w1.char = ? AND wr.relation_type IN ('syn','ant','semantic_related')
  UNION ALL
  SELECT wr.relation_type, w1.char, wr.source, wr.score, w1.jyutping, w1.code, wr.group_codes
  FROM words w2
  JOIN word_relations wr ON wr.related_id = w2.id
  JOIN words w1 ON w1.id = wr.word_id
  WHERE w2.char = ? AND wr.relation_type IN ('syn','ant','semantic_related')
`;

export async function fetchDbRelations(db: Database, query: string): Promise<RelationPoolItem[]> {
  const q = query.trim();
  if (!q) {
    return [];
  }
  const rows = await queryRows(db, BIDIRECTIONAL_REL_ROWS_SQL, [q, q]);
  const items: RelationPoolItem[] = [];
  for (const row of rows) {
    const source = String(row.source ?? 'word_relations');
    if (RUNTIME_DERIVED_ANT_SOURCES.has(source)) {
      continue;
    }
    const rchar = poolLiteral(String(row.rchar ?? ''));
    if (!rchar || rchar === q) {
      continue;
    }
    const relation = String(row.relation_type ?? '') as RelationKind;
    if (!['syn', 'ant', 'semantic_related'].includes(relation)) {
      continue;
    }
    const groupCodes = parseGroupCodes(row.group_codes);
    items.push({
      char: rchar,
      relation,
      source,
      score: row.score == null ? null : Number(row.score),
      in_db: false,
      jyutping: String(row.jyutping ?? ''),
      code: String(row.code ?? ''),
      group_codes: groupCodes,
      _sort: finalScore(source, row.score == null ? null : Number(row.score), false),
    });
  }
  const best = new Map<string, RelationPoolItem>();
  for (const item of items) {
    const key = `${item.char}\t${item.relation}`;
    const prev = best.get(key);
    if (!prev || item._sort < prev._sort) {
      best.set(key, item);
    }
  }
  return [...best.values()];
}

export function staticRelationPool(
  relation: RelationKind,
  words: string[],
  present: Set<string>,
): RelationPoolItem[] {
  return filterStaticWords(words).map((w) => ({
    char: w,
    relation,
    source: 'runtime_static',
    score: null,
    in_db: present.has(w),
    jyutping: '',
    code: '',
    group_codes: [],
    _sort: finalScore('runtime_static', 0.5, present.has(w)),
  }));
}

export function applyInDbMembership(items: RelationPoolItem[], present: Set<string>): RelationPoolItem[] {
  return items.map((item) => {
    const inDb = present.has(item.char);
    return {
      ...item,
      in_db: inDb,
      _sort: finalScore(item.source, item.score, inDb),
    };
  });
}

export function collectSortedPool(
  query: string,
  relation: 'syn' | 'ant',
  relItems: RelationPoolItem[],
  staticWords: string[],
  present: Set<string>,
  morphemeChars: Set<string>,
): RelationPoolItem[] {
  const dbPool = relItems.filter((i) => i.relation === relation);
  const staticPool = staticRelationPool(relation, staticWords, present);
  const effectiveMorphemes = query.length >= 2 ? morphemeChars : new Set<string>();
  const merged =
    relation === 'syn'
      ? sortSynPool(query, [...mergeRelationPools(dbPool, staticPool).values()], effectiveMorphemes)
      : sortAntPool(query, [...mergeRelationPools(dbPool, staticPool).values()], effectiveMorphemes);

  const out: RelationPoolItem[] = [];
  const seen = new Set<string>();
  for (const item of merged) {
    const ch = item.char;
    if (!ch || ch === query || seen.has(ch)) {
      continue;
    }
    seen.add(ch);
    out.push(item);
  }
  return out;
}

export async function buildRelationPool(
  db: Database,
  query: string,
  options: { includeStatic?: boolean; includeDerivedAnt?: boolean } = {},
): Promise<RelationPoolSnapshot> {
  const includeStatic = options.includeStatic !== false;
  const includeDerivedAnt = options.includeDerivedAnt !== false;
  const q = query.trim();
  if (!q || !CJK_RE.test(q)) {
    return createRelationPoolSnapshot(q, [], [], []);
  }

  let relItems = await fetchDbRelations(db, q);
  let staticSyns: string[] = [];
  let staticAnts: string[] = [];
  if (includeStatic) {
    staticSyns = filterStaticWords(getStaticSynonyms(q));
    staticAnts = filterStaticWords(getStaticAntonyms(q));
    if (q.length === 1) {
      const extra: string[] = [];
      for (const compound of getCuratedAntCompounds()) {
        if (compound.length !== 2 || !compound.includes(q)) {
          continue;
        }
        const other = compound[0] === q ? compound[1]! : compound[0]!;
        if (other && other !== q) {
          extra.push(other);
        }
      }
      staticAnts = [...new Set([...staticAnts, ...extra])];
    }
  }
  const morphemeChars =
    q.length >= 2
      ? morphemeCharsFromWordLists(staticSyns, staticAnts)
      : new Set<string>();

  const candidateChars = new Set<string>();
  for (const item of relItems) {
    candidateChars.add(item.char);
  }
  for (const w of staticSyns) {
    candidateChars.add(w);
  }
  for (const w of staticAnts) {
    candidateChars.add(w);
  }

  const present = await charsPresentInDb(db, candidateChars);
  relItems = applyInDbMembership(relItems, present);

  const synPool = collectSortedPool(q, 'syn', relItems, staticSyns, present, morphemeChars);
  let antPool = collectSortedPool(q, 'ant', relItems, staticAnts, present, morphemeChars);

  if (includeDerivedAnt) {
    const membership = await loadDbCharSet(db);
    const headSyns = new Set(synPool.map((r) => r.char));
    const relAntRows = relItems
      .filter((i) => i.relation === 'ant')
      .map((i) => ({ char: i.char, source: i.source }));
    const effectiveMorphemes = q.length >= 2 ? morphemeChars : new Set<string>();
    antPool = sortAntPool(
      q,
      await appendRuntimeDerivedAntPool(
        q,
        antPool,
        db,
        membership,
        includeStatic,
        effectiveMorphemes,
        headSyns,
        relAntRows,
      ),
      effectiveMorphemes,
    ).filter((item) => item.char && item.char !== q);
  }

  const seenMain = new Set([q, ...synPool.map((r) => r.char), ...antPool.map((r) => r.char)]);
  const semanticPool = relItems.filter((item) => {
    if (item.relation !== 'semantic_related') {
      return false;
    }
    const ch = item.char;
    if (!ch || seenMain.has(ch)) {
      return false;
    }
    seenMain.add(ch);
    return true;
  });

  return createRelationPoolSnapshot(q, synPool, antPool, semanticPool);
}
