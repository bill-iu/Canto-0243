/** Grammar family re-exports (mirror app/services/query_grammar). */
export { CODE_TAIL_MIDDLE, GRAMMAR_PLUS, isFramedEqualsQuery } from './shared.ts';
export type { EqualsQuery } from './shared.ts';
export {
  normalizeQuery,
  isPureDigits,
  hasChineseChars,
  hasJyutpingChars,
} from './normalize.ts';
export { parseHeteronymCodeQuery } from './heteronym.ts';
export { parseDoubledSyllableSyntax, parseRelationSyntax, toMatchSpec as relationToMatchSpec } from './relation.ts';
export {
  parseCodeRefMiddleRhymeQuery,
  parseTripleRhymeAnchorQuery,
  parsePartialRhymeMaskQuery,
  parsePartialInitialMaskQuery,
  parseRhymeAnchorQuery,
  parseDoubleWildcardRhymeQuery,
  parseDoubleWildcardInitialQuery,
  parseCodeRefRhymeContradictionHint,
} from './rhyme.ts';
export { parseWildcardCodeAnchorQuery } from './wca.ts';
export {
  parsePrefixWildcardEqualsQuery,
  parsePrefixWildcardInitialQuery,
  parseSerialPhonemeAnchorQuery,
  prefixWildcardEqualsMissingEqHint,
  parsePureCharsSerialHint,
} from './serial.ts';
export { parseAtTailQuery, parsePlusAnchorQuery } from './plus.ts';
export { looksLikeMaskQuery } from './mask.ts';
