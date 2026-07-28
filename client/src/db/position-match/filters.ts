/**
 * MatchSpec filters barrel — F1–F5 modules under ./filters/ (Phase C PR3).
 */
export {
  matchesCodePositions,
  normalizeMode,
  filterWordsByCodeAndMask,
  narrowByPhonemeAnchors,
  preferredPronunciationRows,
  pickAuthoritativeAmong,
  filterSingleDigitToPreferredReadings,
  buildRequiredCodes,
  denseCodeFromRequired,
  requiredCodesFromDigitString,
  codeDigitStringFromSpec,
  hasCodeDigitConstraints,
  appendCodeDigitSlots,
} from './filters/f1-slot-code.ts';
export {
  anchorPhonemeOptions,
  clearAnchorPhonemeOptionsCache,
  matchesPhonemeAtPosition,
  partialMaskSlotOptions,
  wordPassesPartialInitialMaskSpec,
  wordPassesPartialRhymeMaskSpec,
} from './filters/f2-phoneme-anchor.ts';
export {
  JYUTPING_LETTER_KINDS,
  narrowByJyutpingLetterSlots,
  slotConstraintMatches,
} from './filters/f3-letters.ts';
export { applyMatchSpec, filterCandidatesByMatchSpec } from './filters/apply.ts';
