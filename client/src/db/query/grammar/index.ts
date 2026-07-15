/** Grammar family re-exports (mirror app/services/query_grammar). */
export { CODE_TAIL_MIDDLE, GRAMMAR_PLUS } from './shared.ts';
export {
  buildEqualsMatchSpec,
  isFramedEqualsQuery,
  toMatchSpec as equalsToMatchSpec,
  type EqualsQuery,
} from './equals.ts';
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
  toMatchSpec as rhymeToMatchSpec,
} from './rhyme.ts';
export {
  parseWildcardCodeAnchorQuery,
  toMatchSpec as wcaToMatchSpec,
} from './wca.ts';
export {
  parsePrefixWildcardEqualsQuery,
  parsePrefixWildcardInitialQuery,
  parseSerialPhonemeAnchorQuery,
  prefixWildcardEqualsMissingEqHint,
  parsePureCharsSerialHint,
  toMatchSpec as serialToMatchSpec,
} from './serial.ts';
export { parseAtTailQuery, parsePlusAnchorQuery, toMatchSpec as plusToMatchSpec } from './plus.ts';
export {
  looksLikeMaskQuery,
  parseMaskQuery,
  buildMaskFromSlots,
  isWildcardChar,
  toMatchSpec as maskToMatchSpec,
} from './mask.ts';
