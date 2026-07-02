/**
 * Relation pool builder — port of app/domain/relations/pool_builder.py (subset).
 * ponytail: derived_ant deferred; semantic_related passthrough only
 */
import type { Database } from './sqljs.ts';
import { getCodeVariants } from './code-variants.ts';
import { getStaticAntonyms, getStaticSynonyms } from './thesaurus.ts';
import { appendRuntimeDerivedAntPool } from './derived-ant.ts';

export type RelationKind = 'syn' | 'ant' | 'semantic_related';

export type RelationPoolItem = {
  char: string;
  relation: RelationKind;
  source: string;
  score: number | null;
  in_db: boolean;
  jyutping: string;
  code: string;
  group_codes: string[];
  _sort: number;
};

const CJK_RE = /[\u4e00-\u9fff]/;
const RUNTIME_DERIVED_ANT_SOURCES = new Set(['ant_syn_mirror', 'ant_cilin_exanded']);

const QUERY_SYNONYM_PRIORITY: Record<string, string[]> = {
  快樂: ['開心', '愉快', '高興', '歡樂', '快活', '喜悅', '稱快'],
};

const QUERY_ANTONYM_PRIORITY: Record<string, string[]> = {
  快樂: ['悲傷', '傷心', '難過', '痛苦', '哀傷', '憂愁', '沮喪'],
};

const SOURCE_BASE_RANK: Record<string, number> = {
  manual: 0,
  manual_syn_cluster: 18,
  manual_ant_mirror: 20,
  cilin: 10,
  antisem: 10,
  guotong: 15,
  ant_cilin_exanded: 25,
  ant_syn_bridge: 28,
  cow: 20,
  current_static: 15,
  runtime_static: 80,
  static_thesaurus: 80,
  embedding_cosine: 60,
  word_relations: 50,
};

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

function sourceRank(source: string | null | undefined): number {
  if (!source) {
    return 50;
  }
  for (const [key, rank] of Object.entries(SOURCE_BASE_RANK)) {
    if (source.includes(key)) {
      return rank;
    }
  }
  return 40;
}

function finalScore(source: string | null | undefined, confidence: number | null, inDb: boolean): number {
  const rank = sourceRank(source);
  const conf = confidence ?? 0;
  const bonus = inDb ? 5 : -10;
  return rank + conf * 20 + bonus;
}

function parseGroupCodes(raw: unknown): string[] {
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

function filterStaticWords(words: string[]): string[] {
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

function shouldIncludeSynonym(query: string, candidate: string): boolean {
  if (!candidate || candidate === query) {
    return false;
  }
  if (query.length >= 2 && candidate.length === 1) {
    return false;
  }
  return true;
}

function morphemeCharsFromWordLists(...wordLists: string[][]): Set<string> {
  const out = new Set<string>();
  for (const words of wordLists) {
    for (const s of words) {
      if (s.length === 1) {
        out.add(s);
      }
    }
  }
  return out;
}

function preferredRank(query: string, char: string, table: Record<string, string[]>): number {
  const prefs = table[query] ?? [];
  const idx = prefs.indexOf(char);
  return idx >= 0 ? idx : 999;
}

function cilinGroupRank(item: RelationPoolItem): [number, string, number] {
  const codes = item.group_codes;
  if (!codes.length) {
    return [1, '', 0];
  }
  return [0, codes[codes.length - 1]!, -codes.length];
}

function coreSynBoost(query: string, char: string): number {
  if (char.length !== query.length) {
    return 1;
  }
  if (query.length >= 2 && /[心快意悅]$/.test(char)) {
    return 0;
  }
  return 1;
}

function coreAntBoost(query: string, char: string): number {
  if (char.length !== query.length) {
    return 1;
  }
  if (query.length >= 2 && /[傷悲苦痛愁慘過]$/.test(char)) {
    return 0;
  }
  return 1;
}

function relevanceKey(
  query: string,
  item: RelationPoolItem,
  morphemeChars: Set<string>,
  kind: 'syn' | 'ant',
): Array<string | number> {
  const char = item.char;
  const qLen = query.length;
  const cLen = char.length;
  const baseSort = item._sort ?? 99;

  if (qLen >= 2 && cLen === 1) {
    return [999, 999, 999, 999, 999, char];
  }

  const lengthTier = cLen === qLen ? 0 : cLen <= qLen + 2 ? 1 : 2;
  const lengthDelta = Math.abs(cLen - qLen);
  const overlap = [...char].filter((ch) => query.includes(ch)).length;
  const startsMorpheme = char.length > 0 && morphemeChars.has(char[0]!);
  const preferred =
    kind === 'syn'
      ? preferredRank(query, char, QUERY_SYNONYM_PRIORITY)
      : preferredRank(query, char, QUERY_ANTONYM_PRIORITY);
  const coreBoost = kind === 'syn' ? coreSynBoost(query, char) : coreAntBoost(query, char);

  const key: Array<string | number> = [lengthTier, preferred];
  if (kind === 'syn') {
    const [hasGroup, leaf, depth] = cilinGroupRank(item);
    key.push(hasGroup, leaf, depth);
  }
  key.push(coreBoost, lengthDelta, startsMorpheme ? 1 : 0, overlap, -baseSort, char);
  return key;
}

function compareKeys(a: Array<string | number>, b: Array<string | number>): number {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const av = a[i] ?? 0;
    const bv = b[i] ?? 0;
    if (av < bv) {
      return -1;
    }
    if (av > bv) {
      return 1;
    }
  }
  return 0;
}

function mergeRelationPools(
  dbPool: RelationPoolItem[],
  staticPool: RelationPoolItem[],
): Map<string, RelationPoolItem> {
  const merged = new Map<string, RelationPoolItem>();
  for (const item of [...dbPool, ...staticPool]) {
    const ch = item.char;
    if (!ch) {
      continue;
    }
    const prev = merged.get(ch);
    if (!prev || (item._sort ?? 99) < (prev._sort ?? 99)) {
      merged.set(ch, item);
    }
  }
  return merged;
}

function sortSynPool(
  query: string,
  pool: RelationPoolItem[],
  morphemeChars: Set<string>,
): RelationPoolItem[] {
  return pool
    .filter((i) => shouldIncludeSynonym(query, i.char))
    .sort((a, b) => compareKeys(relevanceKey(query, a, morphemeChars, 'syn'), relevanceKey(query, b, morphemeChars, 'syn')));
}

function sortAntPool(
  query: string,
  pool: RelationPoolItem[],
  morphemeChars: Set<string>,
): RelationPoolItem[] {
  return pool
    .filter((i) => shouldIncludeSynonym(query, i.char))
    .sort((a, b) => compareKeys(relevanceKey(query, a, morphemeChars, 'ant'), relevanceKey(query, b, morphemeChars, 'ant')));
}

function charsPresentInDb(db: Database, chars: Iterable<string>): Set<string> {
  const unique = [...new Set(chars)].filter(Boolean);
  if (!unique.length) {
    return new Set();
  }
  const present = new Set<string>();
  const chunk = 500;
  for (let i = 0; i < unique.length; i += chunk) {
    const part = unique.slice(i, i + chunk);
    const placeholders = part.map(() => '?').join(',');
    const stmt = db.prepare(`SELECT DISTINCT char FROM words WHERE char IN (${placeholders})`);
    stmt.bind(part);
    while (stmt.step()) {
      const ch = String((stmt.getAsObject() as { char?: string }).char ?? '');
      if (ch) {
        present.add(ch);
      }
    }
    stmt.free();
  }
  return present;
}

function loadDbCharSet(db: Database): Set<string> {
  const stmt = db.prepare('SELECT DISTINCT char FROM words');
  const out = new Set<string>();
  while (stmt.step()) {
    const ch = String((stmt.getAsObject() as { char?: string }).char ?? '');
    if (ch) {
      out.add(ch);
    }
  }
  stmt.free();
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

function fetchDbRelations(db: Database, query: string): RelationPoolItem[] {
  const q = query.trim();
  if (!q) {
    return [];
  }
  const stmt = db.prepare(BIDIRECTIONAL_REL_ROWS_SQL);
  stmt.bind([q, q]);
  const items: RelationPoolItem[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as Record<string, unknown>;
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
  stmt.free();

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

function staticRelationPool(
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

function applyInDbMembership(items: RelationPoolItem[], present: Set<string>): RelationPoolItem[] {
  return items.map((item) => {
    const inDb = present.has(item.char);
    return {
      ...item,
      in_db: inDb,
      _sort: finalScore(item.source, item.score, inDb),
    };
  });
}

function collectSortedPool(
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

export type RelationPoolSnapshot = {
  query: string;
  syns: RelationPoolItem[];
  ants: RelationPoolItem[];
  semantic: RelationPoolItem[];
};

export function buildRelationPool(
  db: Database,
  query: string,
  options: { includeStatic?: boolean; includeDerivedAnt?: boolean } = {},
): RelationPoolSnapshot {
  const includeStatic = options.includeStatic !== false;
  const includeDerivedAnt = options.includeDerivedAnt !== false;
  const q = query.trim();
  if (!q || !CJK_RE.test(q)) {
    return { query: q, syns: [], ants: [], semantic: [] };
  }

  let relItems = fetchDbRelations(db, q);
  let staticSyns: string[] = [];
  let staticAnts: string[] = [];
  if (includeStatic) {
    staticSyns = filterStaticWords(getStaticSynonyms(q));
    staticAnts = filterStaticWords(getStaticAntonyms(q));
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

  const present = charsPresentInDb(db, candidateChars);
  relItems = applyInDbMembership(relItems, present);

  const synPool = collectSortedPool(q, 'syn', relItems, staticSyns, present, morphemeChars);
  let antPool = collectSortedPool(q, 'ant', relItems, staticAnts, present, morphemeChars);

  if (includeDerivedAnt) {
    const membership = loadDbCharSet(db);
    const headSyns = new Set(synPool.map((r) => r.char));
    const relAntRows = relItems
      .filter((i) => i.relation === 'ant')
      .map((i) => ({ char: i.char, source: i.source }));
    const effectiveMorphemes = q.length >= 2 ? morphemeChars : new Set<string>();
    antPool = sortAntPool(
      q,
      appendRuntimeDerivedAntPool(
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

  return { query: q, syns: synPool, ants: antPool, semantic: semanticPool };
}

export function relationLookupItems(
  db: Database,
  seed: string,
  relationKind: 'syn' | 'ant',
  mode: string,
  codePrefix: string | undefined,
  limit: number,
  offset: number,
): RelationPoolItem[] {
  const pool = buildRelationPool(db, seed);
  const allItems =
    relationKind === 'syn' ? pool.syns : relationKind === 'ant' ? pool.ants : [...pool.syns, ...pool.ants, ...pool.semantic];

  const seen = new Set<string>();
  let unique = allItems.filter((item) => {
    if (!item.char || seen.has(item.char)) {
      return false;
    }
    seen.add(item.char);
    return item.in_db;
  });

  if (codePrefix) {
    const variants = new Set(getCodeVariants(codePrefix, mode === 'm2' || mode === '02493' ? 'm2' : 'm1'));
    unique = unique.filter(
      (item) => variants.has(item.code) && item.char.length === codePrefix.length,
    );
  }

  unique.sort((a, b) => (a._sort ?? 99) - (b._sort ?? 99));
  return unique.slice(offset, offset + limit);
}

/** ponytail: runnable self-check — `npx tsx client/scripts/relation-pool-self-check.ts` */
export function relationPoolLogicSelfCheck(db: Database): void {
  const pool = buildRelationPool(db, '開心');
  const chars = pool.syns.filter((i) => i.in_db).map((i) => i.char);
  if (!chars.includes('快樂') || !chars.includes('愉快')) {
    throw new Error(`relationPoolLogicSelfCheck: syns ${chars.join(',')}`);
  }
}
