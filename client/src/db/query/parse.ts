/**
 * 查詢分派 classifier entry — thin chain over grammar/* (P1 #2).
 * Port of app/services/query_parse.py + query_grammar/* families.
 */
import { maskFromCanonicalPlusQuery } from '../plus-grammar.ts';
import { parseJyutpingAnchorQuery as parseJyutpingAnchorFields } from '../jyutping-anchor.ts';
import { normalizePzmode, tryParsePingZeSerial } from '../ping-zak.ts';
import { QueryKind } from '../query-kind.ts';
import { buildLookupLayout } from './lookup-layout.ts';
import type {
  JyutpingAnchorQuery,
  ParsedQuery,
  QueryMode,
} from '../query-types.ts';
import {
  hasChineseChars,
  hasJyutpingChars,
  isFramedEqualsQuery,
  isPureDigits,
  looksLikeMaskQuery,
  normalizeQuery,
  parseAtTailQuery,
  parseCodeRefMiddleRhymeQuery,
  parseCodeRefRhymeContradictionHint,
  parseDoubleWildcardInitialQuery,
  parseDoubleWildcardRhymeQuery,
  parseDoubledSyllableSyntax,
  parseHeteronymCodeQuery,
  parsePartialInitialMaskQuery,
  parsePartialRhymeMaskQuery,
  parsePlusAnchorQuery,
  parsePrefixWildcardEqualsQuery,
  parsePrefixWildcardInitialQuery,
  parsePureCharsSerialHint,
  parseRelationSyntax,
  parseRhymeAnchorQuery,
  parseSerialPhonemeAnchorQuery,
  parseTripleRhymeAnchorQuery,
  parseWildcardCodeAnchorQuery,
  prefixWildcardEqualsMissingEqHint,
  type EqualsQuery,
} from './grammar/index.ts';

export { QueryKind, RouteKind } from '../query-kind.ts';
export { CODE_TAIL_MIDDLE, isFramedEqualsQuery, normalizeQuery } from './grammar/index.ts';
export type { EqualsQuery } from './grammar/index.ts';
export {
  parseHeteronymCodeQuery,
  parseDoubledSyllableSyntax,
  parseRelationSyntax,
  parseCodeRefMiddleRhymeQuery,
  parseTripleRhymeAnchorQuery,
  parseWildcardCodeAnchorQuery,
  parseAtTailQuery,
  parsePlusAnchorQuery,
  parsePrefixWildcardEqualsQuery,
  parsePrefixWildcardInitialQuery,
  parsePartialRhymeMaskQuery,
  parsePartialInitialMaskQuery,
  parseSerialPhonemeAnchorQuery,
  parseRhymeAnchorQuery,
} from './grammar/index.ts';

export { rowToResult, sortMaskFamilyRows } from './result-map.ts';
export {
  CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT,
  codePrefixedWholeWordEqualsEmptyHint,
} from './equals-empty-hint.ts';

export { isJyutpingQuery } from '../jyutping-match.ts';
export {
  isPingZeSerialQuery,
  isRelationSyntaxQuery,
  normalizeQuerySyntax,
} from './mode-detect.ts';

export const JYUTPING_SYN_MODE_HINT =
  '近反義模式只支援漢字查詢。請改打漢字，或切換至 0243模式／02493模式 查粵拼。';

export function resolveFallback0243Mode(fallback?: QueryMode): 'm1' | 'm2' | 'm3' {
  if (fallback === 'm3' || fallback === '394052') {
    return 'm3';
  }
  if (fallback === 'm2' || fallback === '02493') {
    return 'm2';
  }
  return 'm1';
}

import { modeRedirectHint } from '../../mode-meta.ts';
export { modeRedirectHint };

/** Port of jyutping_anchor.parse_jyutping_anchor_query */
export function parseJyutpingAnchorQuery(q: string): JyutpingAnchorQuery | null {
  const fields = parseJyutpingAnchorFields(q);
  if (!fields) {
    return null;
  }
  return { kind: QueryKind.JYUTPING_ANCHOR, ...fields };
}

/** Port of query_parse.try_parse_before_mask */
export function tryParseBeforeMask(q: string): ParsedQuery | null {
  const doubled = parseDoubledSyllableSyntax(q);
  if (doubled) {
    return doubled;
  }

  const heteronym = parseHeteronymCodeQuery(q);
  if (heteronym) {
    return heteronym;
  }

  const relationParsed = parseRelationSyntax(q);
  if (relationParsed) {
    return relationParsed;
  }

  const prefixEqHint = prefixWildcardEqualsMissingEqHint(q);
  if (prefixEqHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: prefixEqHint };
  }

  const pureCharsHint = parsePureCharsSerialHint(q);
  if (pureCharsHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: pureCharsHint };
  }

  const prefixWildcard = parsePrefixWildcardEqualsQuery(q);
  if (prefixWildcard) {
    return prefixWildcard;
  }

  const prefixInitial = parsePrefixWildcardInitialQuery(q);
  if (prefixInitial) {
    return prefixInitial;
  }

  const partialRhyme = parsePartialRhymeMaskQuery(q);
  if (partialRhyme) {
    return partialRhyme;
  }

  const partialInitial = parsePartialInitialMaskQuery(q);
  if (partialInitial) {
    return partialInitial;
  }

  const serialPhoneme = parseSerialPhonemeAnchorQuery(q);
  if (serialPhoneme) {
    return serialPhoneme;
  }

  if (isFramedEqualsQuery(q)) {
    return { kind: QueryKind.EQUALS, raw_q: q } as EqualsQuery;
  }

  const maskLiteral = maskFromCanonicalPlusQuery(q);
  if (maskLiteral) {
    return { kind: QueryKind.MASK, raw_q: maskLiteral };
  }

  const plusAnchor = parsePlusAnchorQuery(q);
  if (plusAnchor) {
    return plusAnchor;
  }

  const literalRef = parseAtTailQuery(q);
  if (literalRef) {
    return literalRef;
  }

  const contradictionHint = parseCodeRefRhymeContradictionHint(q);
  if (contradictionHint) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: contradictionHint };
  }

  const codeRefMiddle = parseCodeRefMiddleRhymeQuery(q);
  if (codeRefMiddle) {
    return codeRefMiddle;
  }

  const doubleWildRhyme = parseDoubleWildcardRhymeQuery(q);
  if (doubleWildRhyme) {
    return doubleWildRhyme;
  }

  const doubleWildInitial = parseDoubleWildcardInitialQuery(q);
  if (doubleWildInitial) {
    return doubleWildInitial;
  }

  const wca = parseWildcardCodeAnchorQuery(q);
  if (wca) {
    return wca;
  }

  const tripleRhyme = parseTripleRhymeAnchorQuery(q);
  if (tripleRhyme) {
    return tripleRhyme;
  }

  const jyutpingAnchor = parseJyutpingAnchorQuery(q);
  if (jyutpingAnchor) {
    return jyutpingAnchor;
  }

  const rhymeAnchor = parseRhymeAnchorQuery(q);
  if (rhymeAnchor) {
    return rhymeAnchor;
  }

  return null;
}

/** Parse query and classify into QueryKind */
export function parseQuery(q: string, opts?: { mode?: QueryMode; pzmode?: 'm1' | 'm2' | 'm3' }): ParsedQuery {
  const normalized = normalizeQuery(q);

  if (opts?.mode === 'pz') {
    if (/[PZ]/.test(normalized)) {
      const plainRhyme = normalized.match(/^([PZ0-9?]+)([\u4e00-\u9fff])=$/);
      if (plainRhyme) {
        const serial = tryParsePingZeSerial(plainRhyme[1]!, opts.pzmode);
        if (serial?.kind === QueryKind.PING_ZE_SERIAL) {
          return { ...serial, anchor: plainRhyme[2]! };
        }
      }
      const masked = normalized.replace(/[PZ]/g, '0');
      const base = tryParseBeforeMask(masked) ?? (looksLikeMaskQuery(masked)
        ? { kind: QueryKind.MASK, raw_q: masked }
        : null);
      if (base?.kind === QueryKind.JYUTPING_ANCHOR) {
        return {
          kind: QueryKind.UNMATCHED,
          raw_q: normalized,
          hint: '平仄模式不支援粵拼錨，請切換 0243搜尋模式。',
        };
      }
      if (base && base.kind !== QueryKind.UNMATCHED) {
        return {
          kind: QueryKind.PING_ZE_SERIAL,
          raw_q: normalized,
          pzmode: normalizePzmode(opts.pzmode),
          base,
        };
      }
      const pingZeParsed = tryParsePingZeSerial(normalized, opts.pzmode);
      if (pingZeParsed) return pingZeParsed;
    }
    if (parseJyutpingAnchorQuery(normalized)) {
      return {
        kind: QueryKind.UNMATCHED,
        raw_q: normalized,
        hint: '平仄模式不支援粵拼錨，請切換 0243搜尋模式。',
      };
    }
  }

  const beforeMask = tryParseBeforeMask(normalized);
  if (beforeMask) {
    return beforeMask;
  }

  if (looksLikeMaskQuery(normalized)) {
    return { kind: QueryKind.MASK, raw_q: normalized };
  }

  if (isPureDigits(normalized)) {
    return { kind: QueryKind.DIGIT_CODE, raw_q: normalized };
  }

  if (hasChineseChars(normalized)) {
    return { kind: QueryKind.WORD_LOOKUP, raw_q: normalized };
  }

  if (hasJyutpingChars(normalized)) {
    return { kind: QueryKind.JYUTPING_FRAGMENT, raw_q: normalized };
  }

  return { kind: QueryKind.UNMATCHED, raw_q: normalized, hint: '無法辨認的查詢語法' };
}

/** Normalize and parse query */
export function normalizeAndParse(q: string, opts?: { mode?: QueryMode; pzmode?: 'm1' | 'm2' | 'm3' }): ParsedQuery {
  return parseQuery(normalizeQuery(q), opts);
}

/** ponytail: runnable self-check — `npx tsx client/scripts/parser-self-check.ts` */
export function parserLogicSelfCheck(): void {
  const cases: Array<[string, QueryKind]> = [
    ['=窮?潦倒', QueryKind.PARTIAL_INITIAL_MASK],
    ['04困=49倒=', QueryKind.SERIAL_PHONEME],
    ['?yut?', QueryKind.JYUTPING_ANCHOR],
    ['3m4', QueryKind.JYUTPING_ANCHOR],
    ['?hon', QueryKind.JYUTPING_ANCHOR],
    ['3+hon4', QueryKind.JYUTPING_ANCHOR],
    ['23o', QueryKind.JYUTPING_ANCHOR],
    ['34p', QueryKind.JYUTPING_ANCHOR],
    ['34+p', QueryKind.JYUTPING_ANCHOR],
    ['3+p4', QueryKind.JYUTPING_ANCHOR],
    ['3?p4', QueryKind.JYUTPING_ANCHOR],
    ['34gw', QueryKind.JYUTPING_ANCHOR],
    ['3hon4', QueryKind.JYUTPING_ANCHOR],
    ['3$漢4', QueryKind.JYUTPING_ANCHOR],
    ['3+ngo4', QueryKind.JYUTPING_ANCHOR],
    ['23+o', QueryKind.JYUTPING_ANCHOR],
    ['就=', QueryKind.RHYME_ANCHOR],
    ['?+就=', QueryKind.RHYME_ANCHOR],
    ['?+人=?', QueryKind.TRIPLE_RHYME_ANCHOR],
    ['?30人', QueryKind.WILDCARD_CODE_ANCHOR],
    ['12/12', QueryKind.HETERONYM_CODE],
    ['33~與~你', QueryKind.COMPOUND_CONNECT_SYN],
    ['?=困潦倒', QueryKind.PREFIX_WILDCARD_EQUALS],
    ['$$$', QueryKind.COMPOUND_DOUBLED_SYLLABLE],
  ];
  for (const [q, kind] of cases) {
    const parsed = normalizeAndParse(q);
    if (parsed.kind !== kind) {
      throw new Error(`parserLogicSelfCheck: ${q} → ${parsed.kind}, want ${kind}`);
    }
  }
  const codeRef = parseCodeRefMiddleRhymeQuery('?3人=?');
  if (!codeRef || codeRef.anchor !== '人' || codeRef.width !== 3) {
    throw new Error('parserLogicSelfCheck: code_ref_middle parse');
  }
  const missingEq = normalizeAndParse('?困潦倒');
  if (missingEq.kind !== QueryKind.UNMATCHED || !missingEq.hint?.includes('尾格')) {
    throw new Error('parserLogicSelfCheck: prefix wildcard missing = hint');
  }
  const pingze = normalizeAndParse('PZ?', { mode: 'pz', pzmode: 'm1' });
  if (pingze.kind !== QueryKind.PING_ZE_SERIAL || pingze.raw_q !== 'PZ?') {
    throw new Error('parserLogicSelfCheck: pingze slot parse');
  }
  const pingzeRhyme = normalizeAndParse('PZ好=', { mode: 'pz', pzmode: 'm1' });
  if (pingzeRhyme.kind !== QueryKind.PING_ZE_SERIAL || pingzeRhyme.anchor !== '好') {
    throw new Error('parserLogicSelfCheck: pingze rhyme anchor parse');
  }
  const pingzePlus = normalizeAndParse('PZ+好=', { mode: 'pz', pzmode: 'm1' });
  if (pingzePlus.kind !== QueryKind.PING_ZE_SERIAL || !pingzePlus.base) {
    throw new Error('parserLogicSelfCheck: pingze existing anchor parse');
  }
}

/** ponytail: runnable self-check — `npx tsx client/scripts/lookup-layout-self-check.ts` */
export async function lookupLayoutSelfCheck(): Promise<void> {
  const rows = [{ char: '事業', code: '22', jyutping: 'si6 jip6' }];
  const layout = await buildLookupLayout('事業', rows, null);
  const words = layout.map((r) => r.word);
  if (words.length !== 1 || words[0] !== '事業') {
    throw new Error(`lookupLayoutSelfCheck: got ${words.join(',')}`);
  }
  if (layout.some((r) => r.resultType === 'code' || r.resultType === 'jyutping')) {
    throw new Error('lookupLayoutSelfCheck: must not emit code/jyutping headers');
  }
}
