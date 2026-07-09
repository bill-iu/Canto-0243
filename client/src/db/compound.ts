/**
 * Compound query execution — port of app/domain/relations/compound_*.py (P2 subset)
 * ponytail: DB syn/ant graph + static cilin/guotong syn (prebuild index)
 */
import type { Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import { ensureConnectiveCompoundRows } from './db-patch.ts';
import { matchesCodePositions, requiredCodesFromDigitString } from './position-match/filters/f1-slot-code.ts';
import { compareSearchResults } from './ranking.ts';
import { getStaticSynonyms } from './thesaurus.ts';
import { FILLWORD_CONNECTIVES_SET as FILLWORD_CONNECTIVES } from './_generated/fillword-connectives.ts';

export type CompoundKind = 'syn' | 'ant' | 'doubled_syllable';

export interface CompoundSearchSpec {
  compound_kind: CompoundKind;
  width: number;
  code_prefix?: string;
  rhyme_char?: string;
  connective?: string;
}

type WordRow = Record<string, unknown>;
type TierMap = Map<string, number>;

const TIER_CURATED = 0;
const TIER_MORPHEME = 1;
const TIER_SYNTHESIZED = 2;
const NEIGHBOR_K = 12;

let curatedSyn = new Set<string>();
let curatedAnt = new Set<string>();
let synTiersCache: TierMap | null = null;
let antTiersCache: TierMap | null = null;
const doubledCaches = new Map<number, TierMap>();

const MIN_DOUBLED_WIDTH = 2;
const MAX_DOUBLED_WIDTH = 4;

export function getCuratedAntCompounds(): Set<string> {
  return curatedAnt;
}

export function initCompoundLists(data: { syn?: string[]; ant?: string[] }): void {
  if (data.syn) {
    curatedSyn = new Set(data.syn);
  }
  if (data.ant) {
    curatedAnt = new Set(data.ant);
  }
  synTiersCache = null;
  antTiersCache = null;
}

export function resetCompoundCaches(): void {
  synTiersCache = null;
  antTiersCache = null;
  doubledCaches.clear();
}

export function parseCompoundList(text: string): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    for (const token of trimmed.replace(/，/g, ' ').replace(/,/g, ' ').split(/\s+/)) {
      const ch = token.trim();
      if (ch.length !== 2 || seen.has(ch)) {
        continue;
      }
      seen.add(ch);
      out.push(ch);
    }
  }
  return out;
}

/** Fetch curated compound lists from public/ (browser) or skip if missing */
export async function loadCompoundListsFromUrl(baseUrl: string): Promise<void> {
  const root = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  const synRes = await fetch(`${root}data/syn_ant/compound_synonyms.txt`);
  const antRes = await fetch(`${root}data/syn_ant/compound_antonyms.txt`);
  const syn = synRes.ok ? parseCompoundList(await synRes.text()) : [];
  const ant = antRes.ok ? parseCompoundList(await antRes.text()) : [];
  initCompoundLists({ syn, ant });
}

async function loadTwoCharLiterals(db: Database): Promise<Set<string>> {
  const rows = await queryRows(db, `
    SELECT DISTINCT char FROM words
    WHERE length = 2 OR ((length IS NULL OR length = 0) AND length(char) = 2)
  `);
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String((row as WordRow).char ?? '');
    if (ch.length === 2) {
      out.add(ch);
    }
  }
  return out;
}

async function loadSingleCharLiterals(db: Database): Promise<Set<string>> {
  const rows = await queryRows(db, `
    SELECT DISTINCT char FROM words
    WHERE length = 1 OR ((length IS NULL OR length = 0) AND length(char) = 1)
  `);
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String((row as WordRow).char ?? '');
    if (ch.length === 1) {
      out.add(ch);
    }
  }
  return out;
}

async function loadSynAdjacency(db: Database, membership?: Set<string>): Promise<Map<string, Set<string>>> {
  const adj = new Map<string, Set<string>>();
  const rows = await queryRows(db, `
    SELECT w1.char AS a, w2.char AS b
    FROM words w1
    JOIN word_relations wr ON wr.word_id = w1.id
    JOIN words w2 ON w2.id = wr.related_id
    WHERE wr.relation_type = 'syn' AND w1.char != w2.char
  `);
  for (const row of rows) {
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

async function loadAntOrientedPairs(db: Database): Promise<Set<string>> {
  const pairs = new Set<string>();
  const rows = await queryRows(db, `
    SELECT w1.char AS a, w2.char AS b
    FROM words w1
    JOIN word_relations wr ON wr.word_id = w1.id
    JOIN words w2 ON w2.id = wr.related_id
    WHERE wr.relation_type = 'ant' AND w1.char != w2.char
  `);
  for (const row of rows) {
    const a = String(row.a ?? '');
    const b = String(row.b ?? '');
    if (a && b) {
      pairs.add(`${a}\t${b}`);
    }
  }
  return pairs;
}

function expandPairSymmetry(compounds: Set<string>, twoChar: Set<string>): Set<string> {
  const out = new Set(compounds);
  for (const ch of compounds) {
    if (ch.length !== 2) {
      continue;
    }
    const rev = ch[1]! + ch[0]!;
    if (twoChar.has(rev)) {
      out.add(rev);
    }
  }
  return out;
}

function scanMorphemeSynCompounds(
  twoChar: Set<string>,
  synAdj: Map<string, Set<string>>,
  antPairs: Set<string>,
): Set<string> {
  const out = new Set<string>();
  for (const compound of twoChar) {
    if (compound.length !== 2) {
      continue;
    }
    const a = compound[0]!;
    const b = compound[1]!;
    if (a === b || antPairs.has(`${a}\t${b}`)) {
      continue;
    }
    if (synAdj.get(a)?.has(b)) {
      out.add(compound);
    }
  }
  return out;
}

function scanMorphemeAntCompounds(twoChar: Set<string>, antPairs: Set<string>): Set<string> {
  const out = new Set<string>();
  for (const compound of twoChar) {
    if (compound.length !== 2) {
      continue;
    }
    const a = compound[0]!;
    const b = compound[1]!;
    if (a === b) {
      continue;
    }
    if (antPairs.has(`${a}\t${b}`)) {
      out.add(compound);
    }
  }
  return out;
}

function syllableLetters(token: string): string {
  return token.replace(/[1-6]$/i, '').toLowerCase();
}

export function rowHasUniformSyllableLetters(jyutping: string, width: number): boolean {
  const parts = jyutping.trim().split(/\s+/);
  if (parts.length !== width) {
    return false;
  }
  const letters = parts.map((p) => syllableLetters(p));
  return Boolean(letters[0]) && letters.every((x) => x === letters[0]);
}

function rowHasDoubledSyllables(jyutping: string): boolean {
  return rowHasUniformSyllableLetters(jyutping, MIN_DOUBLED_WIDTH);
}

function getRhymeFinals(word: WordRow): string[] {
  const raw = word.finals;
  if (typeof raw === 'string' && raw.startsWith('[')) {
    try {
      return JSON.parse(raw) as string[];
    } catch {
      /* ponytail: fall through */
    }
  }
  const jyut = String(word.jyutping ?? '').split(/\s+/);
  return jyut.map((s) => syllableLetters(s));
}

async function narrowByRhymeChar(
  db: Database,
  literals: Set<string>,
  width: number,
  rhymeChar: string,
): Promise<Set<string>> {
  if (!rhymeChar || width < MIN_DOUBLED_WIDTH) {
    return literals;
  }
  const tailPos = width - 1;
  const stmt = await db.prepare(`
    SELECT char, jyutping, finals FROM words
    WHERE char = ? AND (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    LIMIT 20
  `);
  const anchorRows = await queryRows(db, `
    SELECT finals, jyutping FROM words WHERE char LIKE ? LIMIT 50
  `, [`%${rhymeChar}%`]);
  const allowedFinals = new Set<string>();
  for (const row of anchorRows) {
    for (const f of getRhymeFinals(row)) {
      allowedFinals.add(f);
    }
  }
  if (!allowedFinals.size) {
    await stmt.free();
    return literals;
  }

  const out = new Set<string>();
  for (const literal of literals) {
    await stmt.bind([literal, width, width]);
    let ok = false;
    while (await stmt.step()) {
      const finals = getRhymeFinals(await stmt.getAsObject() as WordRow);
      if (finals.length > tailPos && allowedFinals.has(finals[tailPos]!)) {
        ok = true;
        break;
      }
    }
    await stmt.reset();
    if (ok) {
      out.add(literal);
    }
  }
  await stmt.free();
  return out;
}

async function buildSynTiers(db: Database): Promise<TierMap> {
  const twoChar = await loadTwoCharLiterals(db);
  const singles = await loadSingleCharLiterals(db);
  const synAdj = await loadSynAdjacency(db, singles);
  const antPairs = await loadAntOrientedPairs(db);
  const morpheme = scanMorphemeSynCompounds(twoChar, synAdj, antPairs);
  const curated = new Set([...curatedSyn].filter((ch) => twoChar.has(ch)));

  const tiers = new Map<string, number>();
  for (const ch of curated) {
    tiers.set(ch, TIER_CURATED);
  }
  for (const ch of morpheme) {
    if (!tiers.has(ch)) {
      tiers.set(ch, TIER_MORPHEME);
    }
  }

  const base = new Set([...curated, ...morpheme]);
  for (const ch of singles) {
    const neighbors = [...(synAdj.get(ch) ?? [])].slice(0, NEIGHBOR_K);
    for (const neighbor of neighbors) {
      if (!neighbor || neighbor === ch) {
        continue;
      }
      for (const compound of [ch + neighbor, neighbor + ch]) {
        if (compound.length !== 2 || !twoChar.has(compound) || base.has(compound)) {
          continue;
        }
        if (!tiers.has(compound)) {
          tiers.set(compound, TIER_SYNTHESIZED);
        }
      }
    }
  }
  return tiers;
}

async function buildAntTiers(db: Database): Promise<TierMap> {
  const twoChar = await loadTwoCharLiterals(db);
  const singles = await loadSingleCharLiterals(db);
  const antPairs = await loadAntOrientedPairs(db);
  const morphemeRaw = scanMorphemeAntCompounds(twoChar, antPairs);
  const curatedRaw = new Set([...curatedAnt].filter((ch) => twoChar.has(ch) && ch.length === 2));
  const curated = expandPairSymmetry(curatedRaw, twoChar);
  const morpheme = expandPairSymmetry(
    new Set([...morphemeRaw].filter((ch) => !curated.has(ch))),
    twoChar,
  );

  const tiers = new Map<string, number>();
  for (const ch of curated) {
    tiers.set(ch, TIER_CURATED);
  }
  for (const ch of morpheme) {
    if (!tiers.has(ch)) {
      tiers.set(ch, TIER_MORPHEME);
    }
  }

  const antAdj = new Map<string, Set<string>>();
  for (const key of antPairs) {
    const [a, b] = key.split('\t');
    if (!a || !b) {
      continue;
    }
    if (!antAdj.has(a)) {
      antAdj.set(a, new Set());
    }
    antAdj.get(a)!.add(b);
  }

  const base = new Set([...curated, ...morpheme]);
  const synth = new Set<string>();
  for (const ch of singles) {
    const neighbors = [...(antAdj.get(ch) ?? [])].slice(0, NEIGHBOR_K);
    for (const neighbor of neighbors) {
      for (const compound of [ch + neighbor, neighbor + ch]) {
        if (compound.length !== 2 || !twoChar.has(compound) || base.has(compound) || synth.has(compound)) {
          continue;
        }
        synth.add(compound);
      }
    }
  }
  for (const ch of expandPairSymmetry(synth, twoChar)) {
    if (!tiers.has(ch)) {
      tiers.set(ch, TIER_SYNTHESIZED);
    }
  }
  return tiers;
}

async function loadThreeCharLiterals(db: Database): Promise<Set<string>> {
  const rows = await queryRows(db, `
    SELECT DISTINCT char FROM words
    WHERE length = 3 OR ((length IS NULL OR length = 0) AND length(char) = 3)
  `);
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String((row as WordRow).char ?? '');
    if (ch.length === 3) {
      out.add(ch);
    }
  }
  return out;
}

function flankTiersFromTwoChar(twoCharTiers: TierMap): Map<string, number> {
  const out = new Map<string, number>();
  for (const [w, tier] of twoCharTiers) {
    if (w.length !== 2) {
      continue;
    }
    for (const pair of [`${w[0]}\t${w[1]}`, `${w[1]}\t${w[0]}`]) {
      const prev = out.get(pair);
      out.set(pair, prev === undefined ? tier : Math.min(prev, tier));
    }
  }
  return out;
}

/** Port of compound_connect.search_connective_compound */
async function searchConnectiveCompound(db: Database, spec: CompoundSearchSpec): Promise<TierMap> {
  const connective = spec.connective;
  if (!connective || !FILLWORD_CONNECTIVES.has(connective) || spec.width !== 3) {
    return new Map();
  }
  await ensureConnectiveCompoundRows(db);
  const twoCharTiers =
    spec.compound_kind === 'ant'
      ? (antTiersCache ??= await buildAntTiers(db))
      : (synTiersCache ??= await buildSynTiers(db));
  const flankTiers = flankTiersFromTwoChar(twoCharTiers);
  if (!flankTiers.size) {
    return new Map();
  }
  const tiers = new Map<string, number>();
  for (const w of await loadThreeCharLiterals(db)) {
    if (w[1] !== connective) {
      continue;
    }
    const tier = flankTiers.get(`${w[0]}\t${w[2]}`);
    if (tier !== undefined) {
      tiers.set(w, tier);
    }
  }
  // ponytail: Python narrow_compound_syn_literals no-op at width 3 — rhyme_char unchanged
  return tiers;
}

async function buildDoubledTiers(db: Database, width: number): Promise<TierMap> {
  const tiers = new Map<string, number>();
  const rows = await queryRows(db, `
    SELECT char, jyutping FROM words
    WHERE length = ? OR ((length IS NULL OR length = 0) AND length(char) = ?)
  `, [width, width]);
  for (const row of rows) {
    const ch = String(row.char ?? '');
    if (ch.length === width && rowHasUniformSyllableLetters(String(row.jyutping ?? ''), width)) {
      tiers.set(ch, TIER_CURATED);
    }
  }
  return tiers;
}

async function tierMapForSpec(db: Database, spec: CompoundSearchSpec): Promise<TierMap> {
  if (spec.connective && spec.width === 3) {
    return searchConnectiveCompound(db, spec);
  }
  if (spec.compound_kind === 'doubled_syllable') {
    if (spec.width < MIN_DOUBLED_WIDTH || spec.width > MAX_DOUBLED_WIDTH) {
      return new Map();
    }
    if (!doubledCaches.has(spec.width)) {
      doubledCaches.set(spec.width, await buildDoubledTiers(db, spec.width));
    }
    return doubledCaches.get(spec.width)!;
  }
  if (spec.compound_kind === 'syn') {
    if (!synTiersCache) {
      synTiersCache = await buildSynTiers(db);
    }
    return synTiersCache;
  }
  if (!antTiersCache) {
    antTiersCache = await buildAntTiers(db);
  }
  return antTiersCache;
}

function matchesCodePrefix(code: string, prefix: string, mode: string): boolean {
  if (!prefix) {
    return true;
  }
  // PR-A: serial per-digit (prefix length may be < word code length)
  const required = requiredCodesFromDigitString(prefix);
  return matchesCodePositions(code, required, mode);
}

async function fetchCompoundRows(db: Database, literals: Set<string>, width: number): Promise<WordRow[]> {
  if (!literals.size) {
    return [];
  }
  const list = [...literals];
  const placeholders = list.map(() => '?').join(', ');
  return queryRows(db, `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE char IN (${placeholders})
      AND (length = ? OR ((length IS NULL OR length = 0) AND length(char) = ?))
  `, [...list, width, width]);
}

export async function searchCompoundTiers(db: Database, spec: CompoundSearchSpec): Promise<TierMap> {
  let tiers = await tierMapForSpec(db, spec);
  if (spec.rhyme_char) {
    const allowed = await narrowByRhymeChar(db, new Set(tiers.keys()), spec.width, spec.rhyme_char);
    const narrowed = new Map<string, number>();
    for (const ch of allowed) {
      const t = tiers.get(ch);
      if (t !== undefined) {
        narrowed.set(ch, t);
      }
    }
    tiers = narrowed;
  }
  return tiers;
}

export interface CompoundResult {
  word: string;
  jyutping: string;
  code: string;
  score: number;
}

export async function executeCompoundSearch(
  db: Database,
  spec: CompoundSearchSpec,
  mode: string,
  limit: number,
  offset: number,
): Promise<CompoundResult[]> {
  const tiers = await searchCompoundTiers(db, spec);
  if (!tiers.size) {
    return [];
  }
  const rows = await fetchCompoundRows(db, new Set(tiers.keys()), spec.width);
  const filtered = rows.filter((row) => {
    const code = String(row.code ?? '');
    if (spec.code_prefix && !matchesCodePrefix(code, spec.code_prefix, mode)) {
      return false;
    }
    if (
      spec.compound_kind === 'doubled_syllable'
      && !rowHasUniformSyllableLetters(String(row.jyutping ?? ''), spec.width)
    ) {
      return false;
    }
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const ta = tiers.get(String(a.char ?? '')) ?? 99;
    const tb = tiers.get(String(b.char ?? '')) ?? 99;
    if (ta !== tb) {
      return ta - tb;
    }
    return compareSearchResults(a, b);
  });

  return sorted.slice(offset, offset + limit).map((row) => ({
    word: String(row.char ?? ''),
    jyutping: String(row.jyutping ?? ''),
    code: String(row.code ?? ''),
    score: 0,
  }));
}

/** MF-5 F5: compound candidate rows for position-match source injection */
export async function fetchCompoundWordRows(
  db: Database,
  spec: CompoundSearchSpec,
  mode: string,
): Promise<WordRow[]> {
  const tiers = await searchCompoundTiers(db, spec);
  if (!tiers.size) {
    return [];
  }
  const rows = await fetchCompoundRows(db, new Set(tiers.keys()), spec.width);
  return rows.filter((row) => {
    const code = String(row.code ?? '');
    if (spec.code_prefix && !matchesCodePrefix(code, spec.code_prefix, mode)) {
      return false;
    }
    if (
      spec.compound_kind === 'doubled_syllable'
      && !rowHasUniformSyllableLetters(String(row.jyutping ?? ''), spec.width)
    ) {
      return false;
    }
    return true;
  });
}

/** ponytail: runnable self-check — `npx tsx client/scripts/compound-self-check.ts` */
export function compoundLogicSelfCheck(): void {
  resetCompoundCaches();
  initCompoundLists({ syn: ['朋友'], ant: ['愛憎'] });
}
