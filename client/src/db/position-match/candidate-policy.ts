/**
 * CandidateSource truncation contract (Phase C PR3 / grill C3).
 * Portable: cache-first, then SQL with fallback_limit.
 * PWA: SQL adapter; default cap CANDIDATE_FALLBACK_LIMIT unless unlimited.
 */

/** Default SQL/cache-miss length-bucket cap (both adapters). */
export const CANDIDATE_FALLBACK_LIMIT = 2000;

/**
 * When true, length-bucket query must not apply LIMIT.
 * Used for phoneme/jyutping letter anchors needing full-bucket parity with word_cache.
 */
export function lengthBucketNeedsUnlimited(options: {
  unlimited?: boolean;
}): boolean {
  return options.unlimited === true;
}
