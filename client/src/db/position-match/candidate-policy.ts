/**
 * CandidateSource truncation contract (P3 #7).
 * Limit SSOT: contracts/candidate-source-policy.json → _generated.
 * Portable: cache-first, then SQL with fallback_limit.
 * PWA: SQL adapter; default cap unless unlimited flag.
 */
export { CANDIDATE_FALLBACK_LIMIT } from '../_generated/candidate-source-policy.ts';

/**
 * When true, length-bucket query must not apply LIMIT.
 * Used for phoneme/jyutping letter anchors needing full-bucket parity with word_cache.
 * (Flag is adapter-owned; not enumerated in the policy contract.)
 */
export function lengthBucketNeedsUnlimited(options: {
  unlimited?: boolean;
}): boolean {
  return options.unlimited === true;
}
