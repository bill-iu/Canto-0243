/**
 * Equals span execution — port of position_match/filters.query_words_by_equals_spec (MF-5 F4)
 */
import { getCodeVariants } from '../code-variants.ts';
import { queryFirst, queryRows } from '../database-backend.ts';
import { rhymeFinalsFromJyutping } from '../jyutping-codec.ts';
import type { Database } from '../sqljs.ts';
import { pronRankSortValueForWord } from '../ranking.ts';
import { anchorPhonemeOptions } from './filters.ts';
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

async function equalsAuthoritativeRow(db: Database, literal: string): Promise<WordRow | null> {
  return await queryFirst(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ? LIMIT 1',
    [literal],
  ) as WordRow | null;
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

async function equalsAuthoritativeRowForCode(
  db: Database,
  literal: string,
  codePrefix: string,
  mode: 'm1' | 'm2',
): Promise<WordRow | null> {
  const variants = new Set(getCodeVariants(codePrefix, mode));
  const rows = await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
    [literal],
  );
  const matching = rows.filter((row) => variants.has(getWordCode(row)));
  return preferredPronunciationRow(matching);
}

async function inferRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): Promise<string[] | null> {
  const rows = await queryRows(
    db,
    'SELECT char, initials, finals, jyutping FROM words WHERE char LIKE ? LIMIT 200',
    [`%${literal}%`],
  );
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  for (const row of rows) {
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
      return [parts[idx]!];
    }
  }
  return null;
}

async function equalsRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): Promise<string[] | null> {
  const row = await equalsAuthoritativeRow(db, literal);
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

async function suffixAlignedRefPhonemeParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): Promise<string[] | null> {
  const refLen = literal.length;
  if (refLen < 2) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }
  const rows = await queryRows(
    db,
    'SELECT char, initials, finals, jyutping, length FROM words WHERE char LIKE ? LIMIT 500',
    [`%${literal}`],
  );
  const suffixRows: WordRow[] = [];
  for (const row of rows) {
    if (getWordText(row).endsWith(literal)) {
      suffixRows.push(row);
    }
  }
  const longer = suffixRows.filter((r) => getWordText(r).length > refLen);
  const exact = suffixRows.filter((r) => getWordText(r).length === refLen);
  const pool = longer.length ? longer : exact;
  if (!pool.length) {
    return equalsRefPhonemeParts(db, literal, dimension);
  }
  const row = preferredPronunciationRow(pool);
  return row ? phonemePartsSuffix(row, dimension, refLen) : equalsRefPhonemeParts(db, literal, dimension);
}

async function buildFinalOptionsAtPositions(
  db: Database,
  refChars: string,
  startPos: number,
  width: number,
): Promise<Array<Set<string> | null>> {
  const target: Array<Set<string> | null> = Array.from({ length: width }, () => null);
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos >= 0 && pos < width) {
      const opts = await anchorPhonemeOptions(db, refChars[i]!, 'final');
      if (opts.size) {
        target[pos] = opts;
      }
    }
  }
  return target;
}

function matchesHybridRefChars(
  wordChar: string,
  wordFinals: string[],
  refChars: string,
  startPos: number,
  targetFinalOptions: Array<Set<string> | null>,
): boolean {
  const width = targetFinalOptions.length;
  if (wordChar.length !== width || wordFinals.length !== width) {
    return false;
  }
  for (let i = 0; i < refChars.length; i++) {
    const pos = startPos + i;
    if (pos < 0 || pos >= width) {
      return false;
    }
    if (wordChar[pos] === refChars[i]) {
      continue;
    }
    const options = targetFinalOptions[pos];
    if (options?.size && wordFinals[pos] && options.has(wordFinals[pos]!)) {
      continue;
    }
    return false;
  }
  return true;
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

async function equalsWholeWordMatches(
  spec: MatchSpec,
  db: Database,
  mode: 'm1' | 'm2',
  target: WordRow,
  targetParts: string[],
  isFinal: boolean,
): Promise<WordRow[]> {
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

  const rows = await queryRows(db, sql, params);
  const out: WordRow[] = [];
  for (const word of rows) {
    if (!wordMatchesWidth(word, width)) {
      continue;
    }
    const parts = isFinal ? getRhymeFinals(word) : getWordParts(word, 'initials');
    if (parts.join('\0') === targetKey) {
      out.push(word);
    }
  }
  return out;
}

/** Port of query_words_by_equals_spec */
export async function queryWordsByEqualsSpec(
  spec: MatchSpec,
  db: Database,
  mode = 'm1',
): Promise<WordRow[]> {
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
    targetParts = await suffixAlignedRefPhonemeParts(db, span.ref_literal, span.dimension);
    if (!targetParts) {
      return [];
    }
  } else if (span.whole_word) {
    if (fullCode && spec.width === 4) {
      target =
        (await equalsAuthoritativeRowForCode(db, span.ref_literal, fullCode, searchMode)) ??
        (await equalsAuthoritativeRow(db, span.ref_literal));
    } else {
      target = await equalsAuthoritativeRow(db, span.ref_literal);
    }
    if (!target) {
      return [];
    }
    targetParts = isFinal ? getRhymeFinals(target) : getWordParts(target, 'initials');
    if (!targetParts.length) {
      return [];
    }
  } else {
    // ponytail: infer via substring when no standalone row (parity with executeCodeAnchoredEquals / lexicon inject)
    targetParts = await equalsRefPhonemeParts(db, span.ref_literal, span.dimension);
    if (!targetParts) {
      return [];
    }
  }

  if (span.whole_word) {
    if (!target) {
      return [];
    }
    return equalsWholeWordMatches(spec, db, searchMode, target, targetParts, isFinal);
  }

  const tailRhymeUnion =
    isFinal &&
    Boolean(fullCode) &&
    !span.whole_word &&
    !span.phoneme_anchor_only;

  const [candidates] = await getCandidatesForLength(db, spec.width, {
    code: fullCode || null,
    mode: searchMode,
    unlimited: prefixWildcard || tailRhymeUnion,
  });

  if (tailRhymeUnion) {
    const targetFinalOptions = await buildFinalOptionsAtPositions(
      db,
      span.ref_literal,
      span.start_pos,
      spec.width,
    );
    return candidates.filter(
      (word) =>
        wordMatchesWidth(word, spec.width) &&
        matchesHybridRefChars(
          getWordText(word),
          getRhymeFinals(word),
          span.ref_literal,
          span.start_pos,
          targetFinalOptions,
        ),
    );
  }

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
