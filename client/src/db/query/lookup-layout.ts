/** 詞條 lookup 版面 — port of domain lookup_layout (Arch Phase B). */
import type { Database } from '../sqljs.ts';
import { queryFirst, queryRows } from '../database-backend.ts';
import { sortWordRows } from '../ranking.ts';
import { getCandidatesForLength } from '../position-match/sources.ts';
import { rhymeFinalsFromJyutping } from '../jyutping-codec.ts';
import type { QueryResult } from '../query-types.ts';
import type { WordRow } from '../position-match/word-row.ts';
import { rowToResult } from './parse.ts';

export function deduplicateWordRows(rows: WordRow[]): WordRow[] {
  const seen = new Set<string>();
  const out: WordRow[] = [];
  for (const row of rows) {
    const c = String(row.char ?? '');
    if (!c || seen.has(c)) {
      continue;
    }
    seen.add(c);
    out.push(row);
  }
  return out;
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

function getWordParts(row: WordRow, field: 'initials' | 'finals'): string[] {
  return loadJsonList(row[field]);
}

function getRhymeFinals(row: WordRow): string[] {
  const fromCol = getWordParts(row, 'finals');
  if (fromCol.length) {
    return fromCol;
  }
  const jyut = String(row.jyutping ?? '');
  return jyut ? rhymeFinalsFromJyutping(jyut) : [];
}

async function equalsAuthoritativeRow(db: Database, literal: string): Promise<WordRow | null> {
  return await queryFirst(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
    [literal],
  ) as WordRow | null;
}

function getWordSortCode(row: WordRow): string {
  const code = String(row.code ?? '').trim();
  if (code) {
    return code;
  }
  // ponytail: no jyutping→0243 derive yet
  return '';
}

/** Port of lookup_layout._collect_codes_and_jyuts */
function collectCodesAndJyuts(rows: WordRow[]): {
  codes: string[];
  codeToJyuts: Map<string, string[]>;
} {
  const codes: string[] = [];
  const seenCodes = new Set<string>();
  const codeToJyuts = new Map<string, string[]>();
  for (const row of rows) {
    const c = getWordSortCode(row);
    if (c && /^\d+$/.test(c) && !seenCodes.has(c)) {
      seenCodes.add(c);
      codes.push(c);
    }
    const j = String(row.jyutping ?? '').trim();
    if (c && j) {
      const list = codeToJyuts.get(c) ?? [];
      if (!list.includes(j)) {
        list.push(j);
      }
      codeToJyuts.set(c, list);
    }
  }
  codes.sort((a, b) => Number(a) - Number(b));
  return { codes, codeToJyuts };
}

function finalsJsonForCode(exactMatches: WordRow[], code: string): string | null {
  for (const row of exactMatches) {
    if (getWordSortCode(row) !== code) {
      continue;
    }
    const finalsRaw = row.finals;
    if (finalsRaw) {
      return typeof finalsRaw === 'string' ? finalsRaw : JSON.stringify(finalsRaw);
    }
  }
  return null;
}

async function loadCodeCandidates(db: Database, lenQ: number, codes: string[]): Promise<WordRow[]> {
  if (!codes.length) {
    return [];
  }
  const placeholders = codes.map(() => '?').join(',');
  const rows = await queryRows(
    db,
    `SELECT char, jyutping, code, initials, finals, length FROM words WHERE length = ? AND code IN (${placeholders}) ORDER BY char, jyutping`,
    [lenQ, ...codes],
  ) as WordRow[];
  return sortWordRows(rows);
}

function lookupLiteralChars(q: string): string[] {
  return [...new Set([...q])];
}

function wordSharesLookupLiteral(char: string, literals: string[]): boolean {
  return literals.some((ch) => char.includes(ch));
}

/** 漢字 lookup：同碼同韻含字面 → 同碼其他含字面 → 異碼含字面 */
async function appendLookupLiteralTiers(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    q: string;
    codes: string[];
    exactMatches: WordRow[];
    sameCodeCandidates: WordRow[];
    db: Database;
    lenQ: number;
  },
): Promise<void> {
  const literals = lookupLiteralChars(opts.q);
  if (!literals.length) {
    return;
  }
  const codeSet = new Set(opts.codes);

  for (const code of opts.codes) {
    const finJson = finalsJsonForCode(opts.exactMatches, code);
    if (!finJson) {
      continue;
    }
    const targetFinals = loadJsonList(finJson);
    const sameRhymeLiteral = opts.sameCodeCandidates.filter((row) => {
      if (getWordSortCode(row) !== code) {
        return false;
      }
      if (JSON.stringify(getRhymeFinals(row)) !== JSON.stringify(targetFinals)) {
        return false;
      }
      return wordSharesLookupLiteral(String(row.char ?? ''), literals);
    });
    appendLookupWords(results, seen, sortWordRows(sameRhymeLiteral));
  }

  const sameCodeLiteral = opts.sameCodeCandidates.filter((row) =>
    wordSharesLookupLiteral(String(row.char ?? ''), literals),
  );
  appendLookupWords(results, seen, sortWordRows(sameCodeLiteral));

  const [allLen] = await getCandidatesForLength(opts.db, opts.lenQ, { unlimited: true });
  const diffCodeLiteral = allLen.filter((row) => {
    const code = getWordSortCode(row);
    const ch = String(row.char ?? '');
    return code && !codeSet.has(code) && wordSharesLookupLiteral(ch, literals);
  });
  appendLookupWords(results, seen, sortWordRows(diffCodeLiteral));
}

async function resolveTailRhymeRefFromDb(
  db: Database,
  lastCh: string,
  lenQ: number,
): Promise<{ ref: string | null; pos: number }> {
  const refPos = lenQ > 0 ? Math.max(0, lenQ - 1) : 0;
  if (!lastCh) {
    return { ref: null, pos: refPos };
  }
  const row = await equalsAuthoritativeRow(db, lastCh);
  if (!row) {
    return { ref: null, pos: refPos };
  }
  const fins = getRhymeFinals(row);
  return { ref: fins[0] ?? null, pos: refPos };
}

function appendLookupWords(
  results: QueryResult[],
  seen: Set<string>,
  rows: WordRow[],
): void {
  for (const row of deduplicateWordRows(rows)) {
    const char = String(row.char ?? '');
    if (!char || seen.has(char)) {
      continue;
    }
    seen.add(char);
    results.push({ ...rowToResult(row), resultType: 'word' });
  }
}

function appendPerCodeRhymeSections(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    q: string;
    codes: string[];
    exactMatches: WordRow[];
    candidatesByCode: Map<string, WordRow[]>;
  },
): void {
  const qChars = [...new Set([...opts.q])];
  for (const code of opts.codes) {
    const finJson = finalsJsonForCode(opts.exactMatches, code);
    if (!finJson) {
      continue;
    }
    const targetFinals = loadJsonList(finJson);
    const pool = (opts.candidatesByCode.get(code) ?? [])
      .filter((row) => JSON.stringify(getRhymeFinals(row)) === JSON.stringify(targetFinals))
      .slice(0, 50);
    const sharedChars = new Set(
      pool
        .filter((row) => {
          const text = String(row.char ?? '');
          return qChars.some((ch) => text.includes(ch));
        })
        .map((row) => String(row.char ?? '')),
    );
    const pure = pool.filter((row) => !sharedChars.has(String(row.char ?? '')));
    appendLookupWords(results, seen, sortWordRows(pure).slice(0, 200));
  }
}

function appendTailRhymeSection(
  results: QueryResult[],
  seen: Set<string>,
  opts: {
    codes: string[];
    candidatesByCode: Map<string, WordRow[]>;
    refVal: string | null;
    refPos: number;
  },
): void {
  if (opts.refVal == null) {
    return;
  }
  for (const code of opts.codes) {
    const matched: WordRow[] = [];
    for (const row of (opts.candidatesByCode.get(code) ?? []).slice(0, 50)) {
      const wf = getRhymeFinals(row);
      if (wf.length > opts.refPos && wf[opts.refPos] === opts.refVal) {
        matched.push(row);
      }
    }
    appendLookupWords(results, seen, matched);
  }
}

/** Port of lookup_layout.build_lookup_layout — PWA 略過 code／jyutping 標題列（詞條行已內嵌；Portable 保留） */
export async function buildLookupLayout(
  q: string,
  exactMatches: WordRow[],
  db: Database | null,
): Promise<QueryResult[]> {
  if (!exactMatches.length) {
    return [];
  }
  const results: QueryResult[] = [];
  const seenWords = new Set<string>();
  const lenQ = [...q].length;
  const { codes } = collectCodesAndJyuts(exactMatches);

  appendLookupWords(results, seenWords, exactMatches);
  if (!db || !codes.length) {
    return results;
  }

  const codeSet = new Set(codes);
  const candidates = await loadCodeCandidates(db, lenQ, codes);
  const candidatesByCode = new Map<string, WordRow[]>();
  for (const row of candidates) {
    const code = getWordSortCode(row);
    if (!codeSet.has(code)) {
      continue;
    }
    const list = candidatesByCode.get(code) ?? [];
    list.push(row);
    candidatesByCode.set(code, list);
  }

  await appendLookupLiteralTiers(results, seenWords, {
    q,
    codes,
    exactMatches,
    sameCodeCandidates: candidates,
    db,
    lenQ,
  });

  appendPerCodeRhymeSections(results, seenWords, {
    q,
    codes,
    exactMatches,
    candidatesByCode,
  });

  const { ref, pos } = await resolveTailRhymeRefFromDb(db, q.slice(-1) ?? '', lenQ);
  appendTailRhymeSection(results, seenWords, {
    codes,
    candidatesByCode,
    refVal: ref,
    refPos: pos,
  });
  appendLookupWords(
    results,
    seenWords,
    sortWordRows(candidates.filter((row) => !seenWords.has(String(row.char ?? '')))),
  );
  return results;
}
