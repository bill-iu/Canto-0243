/**
 * Equals span execution — port of position_match/filters.query_words_by_equals_spec (MF-5 F4)
 */
import { getCodeVariants } from '../code-variants.ts';
import { rhymeFinalsFromJyutping } from '../jyutping-codec.ts';
import type { Database } from '../sqljs.ts';
import { pronRankSortValueForWord } from '../ranking.ts';
import { getEqualsSpan, type EqualsDimension, type MatchSpec } from './spec.ts';
import { getCandidatesForLength, wordMatchesWidth } from './sources.ts';
import { getWordCode, getWordParts, getWordText, type WordRow } from './word-row.ts';

function normalizeMode(mode: string): 'm1' | 'm2' {
  return mode === 'm2' || mode === '02493' ? 'm2' : 'm1';
}

function getRhymeFinals(row: WordRow): string[] {
  const fromCol = getWordParts(row, 'finals');
  if (fromCol.length) {
    return fromCol;
  }
  const jyut = String(row.jyutping ?? '');
  return jyut ? rhymeFinalsFromJyutping(jyut) : [];
}

function equalsAuthoritativeRow(db: Database, literal: string): WordRow | null {
  const stmt = db.prepare(
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
  );
  stmt.bind([literal]);
  const row = stmt.step() ? (stmt.getAsObject() as WordRow) : null;
  stmt.free();
  return row;
}

function preferredPronunciationRow(rows: WordRow[]): WordRow | null {
  if (!rows.length) {
    return null;
  }
  const ranked = rows.map((word) => ({
    rank: pronRankSortValueForWord(getWordText(word), String(word.jyutping ?? '')),
    word,
  }));
  const best = Math.min(...ranked.map((r) => r.rank));
  return ranked.find((r) => r.rank === best)?.word ?? rows[0]!;
}

function equalsAuthoritativeRowForCode(
  db: Database,
  literal: string,
  codePrefix: string,
  mode: 'm1' | 'm2',
): WordRow | null {
  const variants = new Set(getCodeVariants(codePrefix, mode));
  const stmt = db.prepare(
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
  );
  stmt.bind([literal]);
  const rows: WordRow[] = [];
  while (stmt.step()) {
    rows.push(stmt.getAsObject() as WordRow);
  }
  stmt.free();
  const matching = rows.filter((row) => variants.has(getWordCode(row)));
  return preferredPronunciationRow(matching);
}

function inferRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping FROM words WHERE char LIKE ? LIMIT 200',
  );
  stmt.bind([`%${literal}%`]);
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    const text = getWordText(row);
    const idx = text.indexOf(literal);
    if (idx < 0) {
      continue;
    }
    const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (!parts.length || idx >= parts.length) {
      continue;
    }
    if (literal.length === 1) {
      stmt.free();
      return [parts[idx]!];
    }
  }
  stmt.free();
  return null;
}

function equalsRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const row = equalsAuthoritativeRow(db, literal);
  if (row) {
    const isFinal = dimension === 'final' || dimension === 'rhyme';
    const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
    return parts.length ? parts : null;
  }
  return inferRefPhonemeParts(db, literal, dimension);
}

function phonemePartsSuffix(
  row: WordRow,
  dimension: EqualsDimension,
  suffixLen: number,
): string[] | null {
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  const parts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
  if (!parts.length || parts.length < suffixLen) {
    return null;
  }
  return parts.slice(-suffixLen);
}

function suffixAlignedRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): string[] | null {
  const refLen = literal.length;
  if (refLen < 2) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }
  const stmt = db.prepare(
    'SELECT char, initials, finals, jyutping, length FROM words WHERE char LIKE ? LIMIT 500',
  );
  stmt.bind([`%${literal}`]);
  const suffixRows: WordRow[] = [];
  while (stmt.step()) {
    const row = stmt.getAsObject() as WordRow;
    if (getWordText(row).endsWith(literal)) {
      suffixRows.push(row);
    }
  }
  stmt.free();
  const longer = suffixRows.filter((r) => getWordText(r).length > refLen);
  const exact = suffixRows.filter((r) => getWordText(r).length === refLen);
  const pool = longer.length ? longer : exact;
  if (!pool.length) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }
  const row = preferredPronunciationRow(pool);
  return row ? phonemePartsSuffix(row, dimension, refLen) : equalsRefPhonemeParts(db, literal, dimension);
}

export function matchesEqualsPhonemeSpan(
  word: WordRow,
  refParts: string[],
  startPos: number,
  opts: {
    phoneme_anchor_only: boolean;
    ref_literal: string;
    dimension: EqualsDimension;
  },
): boolean {
  const charText = getWordText(word);
  if (!opts.phoneme_anchor_only && opts.ref_literal && !charText.includes(opts.ref_literal)) {
    return false;
  }
  const isFinal = opts.dimension === 'final' || opts.dimension === 'rhyme';
  const wordParts = isFinal ? getRhymeFinals(word) : getWordParts(word, 'initials');
  if (!wordParts.length) {
    return false;
  }
  for (let i = 0; i < refParts.length; i++) {
    const pos = startPos + i;
    if (pos >= wordParts.length) {
      return false;
    }
    if (refParts[i] && refParts[i] !== wordParts[pos]) {
      return false;
    }
  }
  return true;
}

function phonemeStorageKey(row: WordRow, field: 'finals' | 'initials'): string {
  const raw = row[field];
  if (typeof raw === 'string') {
    return raw;
  }
  if (Array.isArray(raw)) {
    return JSON.stringify(raw);
  }
  return '';
}

function equalsWholeWordMatches(
  spec: MatchSpec,
  db: Database,
  mode: 'm1' | 'm2',
  target: WordRow,
  targetParts: string[],
  isFinal: boolean,
): WordRow[] {
  const field = isFinal ? 'finals' : 'initials';
  const phonemeKey = phonemeStorageKey(target, field);
  if (!phonemeKey) {
    return [];
  }
  const width = spec.width;
  const fullCode = spec.code_prefix || '';
  const variants = fullCode ? getCodeVariants(fullCode, mode) : [];
  const targetKey = targetParts.join('\0');

  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE ${field} = ?
      AND (
        length = ?
        OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
  `;
  const params: Array<string | number> = [phonemeKey, width, width];
  if (variants.length) {
    sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
    params.push(...variants);
  }
  sql += ' LIMIT 2000';

  const stmt = db.prepare(sql);
  stmt.bind(params);
  const out: WordRow[] = [];
  while (stmt.step()) {
    const word = stmt.getAsObject() as WordRow;
    if (!wordMatchesWidth(word, width)) {
      continue;
    }
    const parts = isFinal ? getRhymeFinals(word) : getWordParts(word, 'initials');
    if (parts.join('\0') === targetKey) {
      out.push(word);
    }
  }
  stmt.free();
  return out;
}

/** Port of query_words_by_equals_spec */
export function queryWordsByEqualsSpec(
  spec: MatchSpec,
  db: Database,
  mode = 'm1',
): WordRow[] {
  const span = getEqualsSpan(spec);
  if (!span) {
    return [];
  }

  const searchMode = normalizeMode(mode);
  const isFinal = span.dimension === 'final' || span.dimension === 'rhyme';
  const prefixWildcard = Boolean(spec.extra?.prefix_wildcard_equals);
  const fullCode = spec.code_prefix || '';

  let targetParts: string[] | null;
  let target: WordRow | null = null;

  if (prefixWildcard) {
    targetParts = suffixAlignedRefPhonemeParts(db, span.ref_literal, span.dimension);
    if (!targetParts) {
      return [];
    }
  } else {
    if (span.whole_word && fullCode && spec.width === 4) {
      target =
        equalsAuthoritativeRowForCode(db, span.ref_literal, fullCode, searchMode) ??
        equalsAuthoritativeRow(db, span.ref_literal);
    } else {
      target = equalsAuthoritativeRow(db, span.ref_literal);
    }
    if (!target) {
      return [];
    }
    targetParts = isFinal ? getRhymeFinals(target) : getWordParts(target, 'initials');
    if (!targetParts.length) {
      return [];
    }
  }

  if (span.whole_word) {
    if (!target) {
      return [];
    }
    return equalsWholeWordMatches(spec, db, searchMode, target, targetParts, isFinal);
  }

  const [candidates] = getCandidatesForLength(db, spec.width, {
    code: fullCode || null,
    mode: searchMode,
  });
  return candidates.filter(
    (word) =>
      wordMatchesWidth(word, spec.width) &&
      matchesEqualsPhonemeSpan(word, targetParts!, span.start_pos, {
        phoneme_anchor_only: span.phoneme_anchor_only,
        ref_literal: span.ref_literal,
        dimension: span.dimension,
      }),
  );
}
