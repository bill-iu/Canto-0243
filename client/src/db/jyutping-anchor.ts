/**
 * Jyutping anchor — thin facade (parse: jyutping-anchor-parse; match: jyutping-anchor-match)
 */
export {
  AMBIGUOUS_PHONEME_LETTERS,
  INITIAL_CLUSTERS,
  classifyLatinAnchor,
  isJyutpingAnchorMaskQuery,
  normalizeRhymeLetters,
  parseJyutpingAnchorQuery,
  rhymeLettersResolveOk,
  type AnchorKind,
  type JyutpingAnchorParsed,
} from './jyutping-anchor-parse.ts';

export {
  buildJyutpingDualMatchSpecs,
  matchesJyutpingAnchorAtPosition,
  parseSyllableLetterTokens,
  toMatchSpec,
} from './jyutping-anchor-match.ts';
