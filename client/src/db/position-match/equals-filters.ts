/**
 * Equals span execution — port of position_match/filters.query_words_by_equals_spec (MF-5 F4)
 */
import { getCodeVariants } from '../code-variants.ts';
import { queryFirst, queryRows } from '../database-backend.ts';
import { rhymeFinalsFromJyutping, splitJyutping } from '../jyutping-codec.ts';
import { compactSpanLikePatterns, encodePhonemeList } from '../phoneme-codec.ts';
import type { Database } from '../sqljs.ts';
import { expandFinalOptions, finalsCompatible } from '../rhyme-match-profile.ts';
import { getRhymeProfile } from '../rhyme-profile-context.ts';
import { pronRankSortValueForWord } from '../ranking.ts';
import { anchorPhonemeOptions } from './filters.ts';
import {
  buildRequiredCodes,
  denseCodeFromRequired,
  matchesCodePositions,
  requiredCodesFromDigitString,
} from './filters/f1-slot-code.ts';
import {
  canonicalizeLegacyMatchSpec,
  type CanonicalMatchSpec,
} from './canonical.ts';
import type { EqualsDimension } from './spec.ts';
import type { MatchSpec } from './spec.ts';
import { getWholeWordLooseFinalIntersect } from './phoneme-index.ts';
import { getCandidatesForLength } from './sources.ts';
import { getWordCode, getWordParts, getWordText, type WordRow } from './word-row.ts';

function denseCodeFromSpec(spec: CanonicalMatchSpec): string {
  return denseCodeFromRequired(buildRequiredCodes(spec)) || '';
}

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
  const required = requiredCodesFromDigitString(codePrefix);
  const rows = await queryRows(
    db,
    'SELECT char, jyutping, code, initials, finals, length FROM words WHERE char = ?',
    [literal],
  );
  const matching = rows.filter((row) => matchesCodePositions(getWordCode(row), required, mode));
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

/** L1: multi-char ref with no headword — assemble one phoneme per canto via authoritative single-char rows */
async function refPhonemePartsPerChar(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
): Promise<string[] | null> {
  if (literal.length < 2) {
    return null;
  }
  const isFinal = dimension === 'final' || dimension === 'rhyme';
  const parts: string[] = [];
  for (const ch of literal) {
    const row = await equalsAuthoritativeRow(db, ch);
    if (!row) {
      return null;
    }
    const slotParts = isFinal ? getRhymeFinals(row) : getWordParts(row, 'initials');
    if (!slotParts.length) {
      return null;
    }
    parts.push(slotParts[0]!);
  }
  return parts;
}

async function resolveEqualsTargetParts(
  db: Database,
  literal: string,
  dimension: EqualsDimension,
  mode: 'prefix' | 'plain',
): Promise<string[] | null> {
  const primary =
    mode === 'prefix'
      ? await suffixAlignedRefPhonemeParts(db, literal, dimension)
      : await equalsRefPhonemeParts(db, literal, dimension);
  if (primary?.length) {
    return primary;
  }
  return refPhonemePartsPerChar(db, literal, dimension);
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
    if (
      options?.size
      && wordFinals[pos]
      && expandFinalOptions(options, getRhymeProfile()).has(wordFinals[pos]!)
    ) {
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
  const profile = getRhymeProfile();
  for (let i = 0; i < refParts.length; i++) {
    const pos = startPos + i;
    if (pos >= wordParts.length) {
      return false;
    }
    const ref = refParts[i];
    if (!ref) continue;
    if (isFinal) {
      if (!finalsCompatible(ref, wordParts[pos]!, profile)) return false;
    } else if (ref !== wordParts[pos]) {
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
    return encodePhonemeList(
      raw.map((x) => (x == null ? '' : String(x))),
      field === 'finals' ? 'final' : 'initial',
    );
  }
  return '';
}

async function equalsWholeWordMatches(
  spec: CanonicalMatchSpec,
  db: Database,
  mode: 'm1' | 'm2',
  target: WordRow | null,
  targetParts: string[],
  isFinal: boolean,
): Promise<WordRow[]> {
  const field = isFinal ? 'finals' : 'initials';
  const phonemeKey = target
    ? phonemeStorageKey(target, field)
    : encodePhonemeList(targetParts, isFinal ? 'final' : 'initial');
  if (!phonemeKey) {
    return [];
  }
  const width = spec.width;
  const fullCode = denseCodeFromSpec(spec);
  const variants = fullCode ? getCodeVariants(fullCode, mode) : [];
  const targetKey = targetParts.join('\0');

  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE ${field} = ?
      AND length = ?
  `;
  const params: Array<string | number> = [phonemeKey, width];
  if (variants.length) {
    sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
    params.push(...variants);
  }
  // 語意完整候選宇宙：phoneme 已在 WHERE；LIMIT 會截斷合法整詞等號命中（len1 initials 桶可 >2000）。

  const rows = await queryRows(db, sql, params);
  const out: WordRow[] = [];
  for (const word of rows) {
    const parts = isFinal ? getRhymeFinals(word) : getWordParts(word, 'initials');
    if (parts.join('\0') === targetKey) {
      out.push(word);
    }
  }
  return out;
}

/** Port of query_words_by_equals_spec */
export async function queryWordsByEqualsSpec(
  input: CanonicalMatchSpec | MatchSpec,
  db: Database,
  mode = 'm1',
): Promise<WordRow[]> {
  const spec = 'candidate_scope' in input ? input : canonicalizeLegacyMatchSpec(input);
  const span = spec.equals_span;
  if (!span) {
    return [];
  }

  const searchMode = normalizeMode(mode);
  const isFinal = span.dimension === 'final' || span.dimension === 'rhyme';
  const prefixWildcard = span.start_pos === 1 && span.phoneme_anchor_only;
  const fullCode = denseCodeFromSpec(spec);

  let targetParts: string[] | null;
  let target: WordRow | null = null;

  if (span.ref_jyutping) {
    const [initials] = splitJyutping(span.ref_jyutping);
    targetParts = isFinal ? rhymeFinalsFromJyutping(span.ref_jyutping) : initials;
    if (targetParts.length !== span.ref_literal.length) return [];
  } else if (prefixWildcard) {
    targetParts = await resolveEqualsTargetParts(db, span.ref_literal, span.dimension, 'prefix');
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
    if (target) {
      targetParts = isFinal ? getRhymeFinals(target) : getWordParts(target, 'initials');
      if (!targetParts.length) {
        return [];
      }
    } else {
      targetParts = await resolveEqualsTargetParts(db, span.ref_literal, span.dimension, 'plain');
      if (!targetParts) {
        return [];
      }
    }
  } else {
    // ponytail: infer via substring / per-char when no standalone multi-char row
    targetParts = await resolveEqualsTargetParts(db, span.ref_literal, span.dimension, 'plain');
    if (!targetParts) {
      return [];
    }
  }

  if (span.whole_word) {
    if (isFinal && getRhymeProfile() !== 'exact') {
      // ADR-0079: runtime ∪/∩ via phoneme index; F1 fallback = full length scan
      const profile = getRhymeProfile();
      let rows = await getWholeWordLooseFinalIntersect(
        db,
        spec.width,
        targetParts!,
        profile,
      );
      if (rows == null) {
        const [scanned] = await getCandidatesForLength(db, spec.width, {
          code: fullCode || null,
          mode: searchMode,
          unlimited: true,
        });
        rows = scanned;
      } else if (fullCode) {
        const required = requiredCodesFromDigitString(fullCode);
        rows = rows.filter((word) => matchesCodePositions(getWordCode(word), required, searchMode));
      }
      return rows.filter((word) =>
        matchesEqualsPhonemeSpan(word, targetParts!, span.start_pos, {
          phoneme_anchor_only: span.phoneme_anchor_only,
          ref_literal: span.ref_literal,
          dimension: span.dimension,
        }),
      );
    }
    return equalsWholeWordMatches(spec, db, searchMode, target, targetParts, isFinal);
  }

  const tailRhymeUnion =
    isFinal &&
    Boolean(fullCode) &&
    !span.whole_word &&
    !span.phoneme_anchor_only;

  // 前綴通配等號：用 finals JSON 預過濾，避免掃晒 ~10 萬個四字詞
  // 放寬韻檔時 LIKE 精準會漏，改 unlimited 再 filter
  let candidates: WordRow[];
  if (
    prefixWildcard
    && targetParts?.length
    && isFinal
    && getRhymeProfile() === 'exact'
  ) {
    candidates = await prefixWildcardCandidatesByFinals(
      db,
      spec.width,
      targetParts,
      fullCode || null,
      searchMode,
    );
  } else {
    // Dense fullCode already narrows; LIMIT before phoneme filter drops hits when
    // m1 variants expand past CANDIDATE_FALLBACK_LIMIT (e.g. 9太=2 → 解毒).
    const [rows] = await getCandidatesForLength(db, spec.width, {
      code: fullCode || null,
      mode: searchMode,
      unlimited: prefixWildcard || tailRhymeUnion || Boolean(fullCode),
    });
    candidates = rows;
  }

  if (tailRhymeUnion) {
    const targetFinalOptions = await buildFinalOptionsAtPositions(
      db,
      span.ref_literal,
      span.start_pos,
      spec.width,
    );
    return candidates.filter(
      (word) =>
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
      matchesEqualsPhonemeSpan(word, targetParts!, span.start_pos, {
        phoneme_anchor_only: span.phoneme_anchor_only,
        ref_literal: span.ref_literal,
        dimension: span.dimension,
      }),
  );
}

/** SQL prefilter for prefix-wildcard equals — P1 compact span LIKE (ADR-0037) */
async function prefixWildcardCandidatesByFinals(
  db: Database,
  width: number,
  targetParts: string[],
  code: string | null,
  mode: 'm1' | 'm2',
): Promise<WordRow[]> {
  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE length = ?
  `;
  const params: Array<string | number> = [width];
  try {
    const encoded = encodePhonemeList(targetParts, 'final');
    const likes = compactSpanLikePatterns(encoded);
    if (likes.length) {
      sql += ` AND (${likes.map(() => 'finals LIKE ?').join(' OR ')})`;
      params.push(...likes);
    }
  } catch {
    // unknown token — fall through to unlimited scan
  }
  if (code) {
    const variants = getCodeVariants(code, mode);
    if (variants.length) {
      sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
      params.push(...variants);
    }
  }
  sql += ' ORDER BY char, jyutping';
  const rows = await queryRows(db, sql, params) as WordRow[];
  if (!rows.length) {
    const [fallback] = await getCandidatesForLength(db, width, {
      code,
      mode,
      unlimited: true,
    });
    return fallback;
  }
  return rows;
}
