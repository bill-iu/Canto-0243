/**
 * Candidate sources — port of app/services/position_match/sources.py (MF-3 + MF-5 F5)
 */
import { fetchCompoundWordRows, type CompoundSearchSpec } from '../compound.ts';
import { getCodeVariants } from '../code-variants.ts';
import { queryRows } from '../database-backend.ts';
import type { Database } from '../sqljs.ts';
import {
  maskCharGlobPattern,
  maskFixedLiteralPrefix,
  matchesMaskLiteralChars,
} from './mask-adapter.ts';
import type { CandidateSource, MatchSpec } from './spec.ts';
import {
  CANDIDATE_FALLBACK_LIMIT,
  lengthBucketNeedsUnlimited,
} from './candidate-policy.ts';

export type WordRow = Record<string, unknown>;
export { CANDIDATE_FALLBACK_LIMIT, lengthBucketNeedsUnlimited } from './candidate-policy.ts';

export function wordMatchesWidth(row: WordRow, width: number): boolean {
  const stored = Number(row.length ?? 0);
  if (stored > 0) {
    return stored === width;
  }
  return String(row.char ?? '').length === width;
}

export type GetCandidatesOptions = {
  code?: string | null;
  mode?: string;
  fallbackLimit?: number;
  /** ponytail: jyutping letter anchors need full length bucket (desktop word_cache parity) */
  unlimited?: boolean;
};

/**
 * 通用長度候選取得（無 mask 預過濾）— port of get_candidates_for_length.
 * ponytail: PWA 無 word_cache，一律走 DB；第二返回值恒 false。
 */
export async function getCandidatesForLength(
  db: Database,
  length: number,
  options: GetCandidatesOptions = {},
): Promise<[WordRow[], boolean]> {
  const mode = options.mode === 'm2' || options.mode === '02493' ? 'm2' : 'm1';
  const limit = options.fallbackLimit ?? CANDIDATE_FALLBACK_LIMIT;
  const unlimited = lengthBucketNeedsUnlimited(options);
  const code = options.code ?? null;

  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
  `;
  const params: Array<string | number> = [length, length];

  if (code) {
    const variants = getCodeVariants(code, mode);
    if (variants.length) {
      sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
      params.push(...variants);
    }
  }

  sql += ' ORDER BY char, jyutping';
  if (!unlimited) {
    sql += ' LIMIT ?';
    params.push(limit);
  }

  const resultRows = await queryRows(db, sql, params);
  const rows: WordRow[] = [];
  for (const row of resultRows) {
    if (wordMatchesWidth(row, length)) {
      rows.push(row);
    }
  }
  return [rows, false];
}

/** Port of sources.get_length_candidates — mask GLOB，唔受 2000 上限 */
export async function getLengthMaskCandidates(
  db: Database,
  length: number,
  mask: string,
  options: { code?: string | null; mode?: string } = {},
): Promise<[WordRow[], boolean]> {
  const mode = options.mode === 'm2' || options.mode === '02493' ? 'm2' : 'm1';
  const globPat = maskCharGlobPattern(mask);
  const prefix = maskFixedLiteralPrefix(mask);
  let sql = `
    SELECT char, jyutping, code, initials, finals, length
    FROM words
    WHERE (
      length = ?
      OR ((length IS NULL OR length = 0) AND length(char) = ?)
    )
    AND char GLOB ?
  `;
  const params: Array<string | number> = [length, length, globPat];
  if (prefix) {
    sql += ' AND char LIKE ?';
    params.push(`${prefix}%`);
  }
  const code = options.code ?? null;
  if (code) {
    const variants = getCodeVariants(code, mode);
    if (variants.length) {
      sql += ` AND code IN (${variants.map(() => '?').join(', ')})`;
      params.push(...variants);
    }
  }
  sql += ' ORDER BY char, jyutping';

  const resultRows = await queryRows(db, sql, params);
  const rows: WordRow[] = [];
  for (const row of resultRows) {
    const text = String(row.char ?? '');
    if (wordMatchesWidth(row, length) && matchesMaskLiteralChars(text, mask)) {
      rows.push(row);
    }
  }
  return [rows, false];
}

function maskWithLiteralAt(width: number, pos: number, ch: string): string {
  return Array.from({ length: width }, (_, i) => (i === pos ? ch : '?')).join('');
}

/** 錨字在固定格的所有 width 詞（partial mask slot options） */
export async function getCandidatesWithLiteralAt(
  db: Database,
  width: number,
  pos: number,
  ch: string,
): Promise<WordRow[]> {
  return (await getLengthMaskCandidates(db, width, maskWithLiteralAt(width, pos, ch)))[0];
}

/** Port of LengthCodeCandidateSource */
export class LengthCodeCandidateSource implements CandidateSource {
  constructor(
    private readonly db: Database,
    private readonly code: string | null = null,
    private readonly mode = 'm1',
    private readonly fallbackLimit = CANDIDATE_FALLBACK_LIMIT,
  ) {}

  async getCandidates(
    length: number,
    options?: { code?: string | null; mode?: string },
  ): Promise<[unknown[], boolean]> {
    const effectiveCode = options?.code !== undefined ? options.code : this.code;
    const effectiveMode = options?.mode ?? this.mode;
    return getCandidatesForLength(this.db, length, {
      code: effectiveCode,
      mode: effectiveMode,
      fallbackLimit: this.fallbackLimit,
    });
  }
}

/** Port of sources._compound_rhyme_char */
export function compoundRhymeChar(spec: MatchSpec): string | undefined {
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' && slot.value) {
      return String(slot.value);
    }
  }
  return undefined;
}

export function compoundSearchSpecFromMatchSpec(spec: MatchSpec): CompoundSearchSpec | null {
  if (!spec.compound_kind) {
    return null;
  }
  const connective = spec.extra?.connective;
  return {
    compound_kind: spec.compound_kind,
    width: spec.width,
    code_prefix: spec.code_prefix ?? undefined,
    rhyme_char: compoundRhymeChar(spec),
    connective: typeof connective === 'string' ? connective : undefined,
  };
}

/** Port of CompoundCandidateSource */
export class CompoundCandidateSource implements CandidateSource {
  constructor(
    private readonly db: Database,
    private readonly compounds: Set<string>,
    private readonly expectedLength = 2,
  ) {}

  async getCandidates(
    length: number,
    _options?: { code?: string | null; mode?: string },
  ): Promise<[WordRow[], boolean]> {
    if (length !== this.expectedLength || !this.compounds.size) {
      return [[], false];
    }
    const list = [...this.compounds];
    const placeholders = list.map(() => '?').join(', ');
    const resultRows = await queryRows(this.db, `
      SELECT char, jyutping, code, initials, finals, length
      FROM words
      WHERE char IN (${placeholders})
        AND (
          length = ?
          OR ((length IS NULL OR length = 0) AND length(char) = ?)
      )
      ORDER BY char, jyutping
    `, [...list, this.expectedLength, this.expectedLength]);
    const rows: WordRow[] = [];
    for (const row of resultRows) {
      if (wordMatchesWidth(row, this.expectedLength)) {
        rows.push(row);
      }
    }
    return [rows, false];
  }
}

/** ponytail: MF-5 F5 compound_kind source — reuses compound.ts tier search */
export async function getCompoundCandidatesForSpec(
  spec: MatchSpec,
  db: Database,
  mode: string,
): Promise<WordRow[]> {
  const compoundSpec = compoundSearchSpecFromMatchSpec(spec);
  if (!compoundSpec) {
    return [];
  }
  return fetchCompoundWordRows(db, compoundSpec, mode);
}

/** ponytail: runnable self-check — needs injected Database */
export async function positionMatchSourcesSelfCheck(db: Database): Promise<void> {
  const [width2] = await getCandidatesForLength(db, 2);
  if (!width2.length) {
    throw new Error('positionMatchSourcesSelfCheck: width=2 bucket empty');
  }
  const sampleCode = String(width2[0]!.code ?? '');
  if (!sampleCode) {
    throw new Error('positionMatchSourcesSelfCheck: sample row missing code');
  }
  const [filtered] = await getCandidatesForLength(db, 2, { code: sampleCode });
  if (!filtered.length) {
    throw new Error('positionMatchSourcesSelfCheck: code filter empty');
  }
  const source = new LengthCodeCandidateSource(db, sampleCode, 'm1');
  const [viaSource] = await source.getCandidates(2);
  if (!viaSource.length) {
    throw new Error('positionMatchSourcesSelfCheck: LengthCodeCandidateSource');
  }
}
