/**
 * Workbench span / line limits (ADR-0069).
 * Keep in sync with app/services/workbench/limits.py and contracts schema.
 */

/** One line / 替換段 hard max (= 工作台起句). */
export const WORKBENCH_MAX_SLOTS = 64;

/**
 * Observed max `words.char` length; skip candidate query when span wider.
 * Independent of relation `MAX_WORD_LEN` (12). ponytail: open-db max(length).
 */
export const WORKBENCH_LEXICON_MAX_WORD_LEN = 20;

/** Phoneme middle checkboxes only when width ≤ this. */
export const WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH = 6;

/** Empty-pool soft tip: sparse band starts here (inclusive). */
export const WORKBENCH_SPARSE_WIDTH_MIN = 5;

/** Empty-pool tip for structural no equal-length word (width > lexicon max). */
export function emptyPoolTip(width: number, visibleCount: number): string | null {
  if (visibleCount > 0 || width < WORKBENCH_SPARSE_WIDTH_MIN) return null;
  if (width > WORKBENCH_LEXICON_MAX_WORD_LEN) {
    return '目前詞庫無呢個字數嘅等長詞；可縮短替換段，或用段手打直接改。';
  }
  return '呢段長度詞庫較少；可改條件、縮短替換段，或用段手打。';
}

export function shouldSkipCandidateQuery(width: number): boolean {
  return width > WORKBENCH_LEXICON_MAX_WORD_LEN;
}
