/** Code-prefixed whole-word equals empty hint. */
import type { Database } from '../sqljs.ts';
import { queryFirst } from '../database-backend.ts';
import { codeDigitStringFromSpec } from '../position-match/filters/f1-slot-code.ts';
import type { CanonicalMatchSpec } from '../position-match/canonical.ts';

export const CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT = 
  '「{literal}」有收錄，但在 0243 碼 {code} 下無整詞同韻結果。';

/**
 * Generate hint for empty results in code-prefixed whole word equals query
 */
export async function codePrefixedWholeWordEqualsEmptyHint(
  spec: CanonicalMatchSpec,
  db: Database
): Promise<string | null> {
  const span = spec.equals_span;
  if (!span || !span.whole_word) {
    return null;
  }
  
  const code = codeDigitStringFromSpec(spec) || '';
  const literal = span.ref_literal;
  
  if (!code || code.length !== literal.length) {
    return null;
  }

  // Check if the literal exists in the database
  const sql = 'SELECT COUNT(*) as count FROM words WHERE char = ?';
  const result = await queryFirst(db, sql, [literal]) ?? { count: 0 };
  
  if (result.count === 0) {
    return null;
  }
  
  // Literal exists but no results - generate hint
  return CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT
    .replace('{literal}', literal)
    .replace('{code}', code);
}
