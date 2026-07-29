/**
 * TS facade for shared/rhyme-match-profile.mjs
 */
import {
  expandFinalOptions as expandFinalOptionsJs,
  expandOneFinal as expandOneFinalJs,
  finalsCompatible as finalsCompatibleJs,
  isRhymeProfile as isRhymeProfileJs,
  normalizeRhymeProfile as normalizeRhymeProfileJs,
  RHYME_PROFILE_LABELS as LABELS,
  RHYME_PROFILES as PROFILES,
} from '../../../shared/rhyme-match-profile.mjs';

export type RhymeProfile = 'exact' | 'tong' | 'nucleus' | 'coda';

export const RHYME_PROFILES = PROFILES as readonly RhymeProfile[];
export const RHYME_PROFILE_LABELS = LABELS as Record<RhymeProfile, string>;

export function isRhymeProfile(value: unknown): value is RhymeProfile {
  return isRhymeProfileJs(value);
}

export function normalizeRhymeProfile(value: unknown): RhymeProfile {
  return normalizeRhymeProfileJs(value) as RhymeProfile;
}

export function expandOneFinal(final: string, profile?: RhymeProfile | string): Set<string> {
  return expandOneFinalJs(final, profile);
}

export function expandFinalOptions(
  options: Iterable<string> | Set<string> | null | undefined,
  profile?: RhymeProfile | string,
): Set<string> {
  return expandFinalOptionsJs(options, profile);
}

export function finalsCompatible(
  a: string,
  b: string,
  profile?: RhymeProfile | string,
): boolean {
  return finalsCompatibleJs(a, b, profile);
}
