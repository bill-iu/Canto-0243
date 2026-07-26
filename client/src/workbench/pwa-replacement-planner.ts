/**
 * Compat barrel — implementation lives in build-match-spec / group-candidates / plan-replacements.
 * Prefer importing those modules directly.
 */
export {
  buildMatchSpec,
  buildPwaMatchSpec,
  compileReplacementPlan,
  matchSpecToCanonical,
} from './build-match-spec.ts';
export { groupCandidates, groupLiterals } from './group-candidates.ts';
export { planPwaReplacements, planReplacements } from './plan-replacements.ts';
