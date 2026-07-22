/**
 * Heteronym code/code query execution — port of heteronym_code_executor.py
 */
import { initSqlJs, type Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import { createSqlJsBackend } from './sqljs-backend.ts';
import { getCodeVariants } from './code-variants.ts';
import { initRankingData, sortHeteronymResults } from './ranking.ts';

type ReadingRow = [string, string];

export interface HeteronymCodeParsed {
  left_template: string;
  right_template: string;
  width: number;
}

export interface HeteronymResult {
  word: string;
  jyutping: string;
  code: string;
  score: number;
  heteronym_tags?: string[];
}

let indexCache: Map<string, ReadingRow[]> | null = null;

export function resetHeteronymIndex(): void {
  indexCache = null;
}

/** Port of heteronym.code_template_to_required */
export function codeTemplateToRequired(template: string): Array<string | null> {
  return [...template].map((ch) => (ch === '?' ? null : ch));
}

function matchesCodeTemplate(
  code: string | number,
  template: Array<string | null>,
  mode: 'm1' | 'm2',
): boolean {
  const codeStr = String(code);
  if (codeStr.length !== template.length) {
    return false;
  }
  for (let i = 0; i < template.length; i++) {
    const req = template[i];
    if (!req) {
      continue;
    }
    const variants = new Set(getCodeVariants(req, mode));
    if (!variants.has(codeStr[i]!)) {
      return false;
    }
  }
  return true;
}

function yieldToMain(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

export async function buildHeteronymIndex(db: Database): Promise<Map<string, ReadingRow[]>> {
  const buckets = new Map<string, ReadingRow[]>();
  const rows = await queryRows(db, 'SELECT char, code, jyutping FROM words');
  let n = 0;
  for (const row of rows) {
    const ch = String(row.char ?? '');
    const jyut = String(row.jyutping ?? '');
    if (!ch || !jyut) {
      continue;
    }
    const list = buckets.get(ch) ?? [];
    list.push([String(row.code ?? ''), jyut]);
    buckets.set(ch, list);
    n += 1;
    if (n % 4000 === 0) {
      await yieldToMain();
    }
  }

  const out = new Map<string, ReadingRow[]>();
  for (const [ch, readings] of buckets) {
    const distinct = new Set(readings.map(([, jp]) => jp));
    if (distinct.size >= 2) {
      out.set(ch, readings);
    }
  }
  return out;
}

async function ensureHeteronymIndex(db: Database): Promise<Map<string, ReadingRow[]>> {
  if (!indexCache) {
    indexCache = await buildHeteronymIndex(db);
  }
  return indexCache;
}

function tagsForReading(
  code: string,
  leftReq: Array<string | null>,
  rightReq: Array<string | null>,
  mode: 'm1' | 'm2',
): string[] {
  const tags: string[] = [];
  if (matchesCodeTemplate(code, leftReq, mode)) {
    tags.push('左');
  }
  if (matchesCodeTemplate(code, rightReq, mode)) {
    tags.push('右');
  }
  return tags;
}

export async function executeHeteronymCodeSearch(
  parsed: HeteronymCodeParsed,
  db: Database,
  mode: string,
  limit: number,
  offset: number,
): Promise<{ items: HeteronymResult[]; total: number }> {
  const searchMode = mode === 'm2' || mode === '02493' ? 'm2' : 'm1';
  const leftReq = codeTemplateToRequired(parsed.left_template);
  const rightReq = codeTemplateToRequired(parsed.right_template);
  const index = await ensureHeteronymIndex(db);
  const matchedChars: string[] = [];

  let scan = 0;
  for (const [ch, readings] of index) {
    scan += 1;
    if (scan % 800 === 0) {
      await yieldToMain();
    }
    if (ch.length !== parsed.width) {
      continue;
    }
    const leftJyuts = new Set<string>();
    const rightJyuts = new Set<string>();
    for (const [code, jyut] of readings) {
      if (matchesCodeTemplate(code, leftReq, searchMode)) {
        leftJyuts.add(jyut);
      }
      if (matchesCodeTemplate(code, rightReq, searchMode)) {
        rightJyuts.add(jyut);
      }
    }
    if (!leftJyuts.size || !rightJyuts.size) {
      continue;
    }
    if (leftJyuts.size === 1 && rightJyuts.size === 1 && [...leftJyuts][0] === [...rightJyuts][0]) {
      continue;
    }
    let paired = false;
    for (const j1 of leftJyuts) {
      for (const j2 of rightJyuts) {
        if (j1 !== j2) {
          paired = true;
          break;
        }
      }
      if (paired) break;
    }
    if (paired) {
      matchedChars.push(ch);
    }
  }

  if (!matchedChars.length) {
    return { items: [], total: 0 };
  }

  // Batch load readings — avoid per-char prepare (was freezing 33/34 on full lexicon)
  const items: HeteronymResult[] = [];
  const chunk = 200;
  for (let i = 0; i < matchedChars.length; i += chunk) {
    const part = matchedChars.slice(i, i + chunk);
    const placeholders = part.map(() => '?').join(',');
    const rows = await queryRows(
      db,
      `SELECT char, jyutping, code, length FROM words WHERE char IN (${placeholders})`,
      part,
    );
    for (const row of rows) {
      const rowChar = String(row.char ?? '');
      const rowLen = Number(row.length ?? rowChar.length);
      if (rowLen !== parsed.width && rowChar.length !== parsed.width) {
        continue;
      }
      const code = String(row.code ?? '');
      const tags = tagsForReading(code, leftReq, rightReq, searchMode);
      if (!tags.length) {
        continue;
      }
      items.push({
        word: rowChar,
        jyutping: String(row.jyutping ?? ''),
        code,
        score: 0,
        heteronym_tags: tags,
      });
    }
    await yieldToMain();
  }

  return {
    items: sortHeteronymResults(items).slice(offset, offset + limit),
    total: matchedChars.length,
  };
}

/** ponytail: runnable self-check — `npx tsx client/scripts/heteronym-self-check.ts` */
export async function heteronymLogicSelfCheck(): Promise<void> {
  const left = codeTemplateToRequired('1?');
  const right = codeTemplateToRequired('?2');
  if (left[0] !== '1' || left[1] !== null || right[1] !== '2') {
    throw new Error('heteronymLogicSelfCheck: template parse');
  }

  const SQL = await initSqlJs();
  const db = new SQL.Database();
  db.run(
    'CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT, length INTEGER)',
  );
  db.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('AB', '35', 'a1 b1', 2)`);
  db.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('AB', '56', 'a2 b2', 2)`);
  resetHeteronymIndex();
  const { items } = await executeHeteronymCodeSearch(
    { left_template: '1?', right_template: '?2', width: 2 },
    createSqlJsBackend(db),
    'm1',
    10,
    0,
  );
  if (items.length !== 2) {
    throw new Error(`heteronymLogicSelfCheck: rows ${items.length}`);
  }

  // heteronym sort self-check: freq primary across chars, pure jyut lexical within char
  initRankingData({
    essay: { '高頻': 100, '低頻': 10 },
  });
  const db2 = new SQL.Database();
  db2.run(
    'CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT, length INTEGER)',
  );
  db2.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('高頻', '35', 'a1 b1', 2)`);
  db2.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('高頻', '56', 'a2 b2', 2)`);
  db2.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('低頻', '35', 'a1 b1', 2)`);
  db2.run(`INSERT INTO words (char, code, jyutping, length) VALUES ('低頻', '56', 'a2 b2', 2)`);
  resetHeteronymIndex();
  const { items: hetItems } = await executeHeteronymCodeSearch(
    { left_template: '1?', right_template: '?2', width: 2 },
    createSqlJsBackend(db2),
    'm1',
    10,
    0,
  );
  const hetOrder = hetItems.map((r) => r.word).join(',');
  if (hetOrder !== '高頻,高頻,低頻,低頻') {
    throw new Error(`heteronymLogicSelfCheck: char order ${hetOrder}`);
  }
  const highJyuts = hetItems
    .filter((r) => r.word === '高頻')
    .map((r) => r.jyutping)
    .join(',');
  if (highJyuts !== 'a1 b1,a2 b2') {
    throw new Error(`heteronymLogicSelfCheck: within-char jyut order ${highJyuts}`);
  }
}
