/** Port of query_grammar/relation. */
import { FILLWORD_CONNECTIVES } from '../../_generated/fillword-connectives.ts';
import { QueryKind } from '../../query-kind.ts';
import type {
  CompoundAntQuery,
  CompoundDoubledSyllableQuery,
  CompoundSynQuery,
  ParsedQuery,
  RelationLookupQuery,
  UnmatchedQuery,
} from '../../query-types.ts';

const DOUBLED_SYLLABLE_MIN_DOLLARS = 2;
const DOUBLED_SYLLABLE_MAX_DOLLARS = 4;
const DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT = '雙聲疊韻字查詢須用 2 至 4 個連續 $。';
const DOUBLED_SYLLABLE_CODE_WIDTH_HINT = '碼位數須與 $ 個數一致（如 333$$$）。';

/** Port of relation.parse_doubled_syllable_syntax */
export function parseDoubledSyllableSyntax(
  q: string,
): CompoundDoubledSyllableQuery | UnmatchedQuery | null {
  const m = q.match(/^(\d*)(\$+)([\u4e00-\u9fff])?$/);
  if (!m) {
    return null;
  }
  const width = m[2]!.length;
  if (width < DOUBLED_SYLLABLE_MIN_DOLLARS || width > DOUBLED_SYLLABLE_MAX_DOLLARS) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT,
    };
  }
  const prefix = m[1] ?? '';
  if (prefix && prefix.length !== width) {
    return {
      kind: QueryKind.UNMATCHED,
      raw_q: q,
      hint: DOUBLED_SYLLABLE_CODE_WIDTH_HINT,
    };
  }
  return {
    kind: QueryKind.COMPOUND_DOUBLED_SYLLABLE,
    raw_q: q,
    width,
    code_prefix: prefix || undefined,
    rhyme_char: m[3] || undefined,
  };
}

/** Port of relation.parse_relation_syntax (compound + single ~ / ! lookup) */
export function parseRelationSyntax(q: string): ParsedQuery | null {
  let m = q.match(
    new RegExp(`^(\\d*)~([${FILLWORD_CONNECTIVES}])~([\u4e00-\u9fff])?$`),
  );
  if (m) {
    return {
      kind: QueryKind.COMPOUND_SYN,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[3] || undefined,
    } as CompoundSynQuery;
  }

  m = q.match(
    new RegExp(`^(\\d*)!([${FILLWORD_CONNECTIVES}])!([\u4e00-\u9fff])?$`),
  );
  if (m) {
    return {
      kind: QueryKind.COMPOUND_ANT,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[3] || undefined,
    } as CompoundAntQuery;
  }

  m = q.match(/^(\d*)~~([\u4e00-\u9fff])?$/);
  if (m) {
    return {
      kind: QueryKind.COMPOUND_SYN,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[2] || undefined,
    } as CompoundSynQuery;
  }

  m = q.match(/^(\d*)!!([\u4e00-\u9fff])?$/);
  if (m) {
    return {
      kind: QueryKind.COMPOUND_ANT,
      raw_q: q,
      code_prefix: m[1] || undefined,
      rhyme_char: m[2] || undefined,
    } as CompoundAntQuery;
  }

  m = q.match(/^(\d*)([~!])([\u4e00-\u9fff]+)$/);
  if (m) {
    return {
      kind: QueryKind.RELATION_LOOKUP,
      raw_q: q,
      relation_kind: m[2] === '~' ? 'syn' : 'ant',
      word: m[3]!,
      code_prefix: m[1] || undefined,
    } as RelationLookupQuery;
  }

  return null;
}
