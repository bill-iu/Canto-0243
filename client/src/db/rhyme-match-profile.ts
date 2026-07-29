/**
 * TS facade for shared/rhyme-match-profile.mjs
 */
import {
  expandFinalOptions as expandFinalOptionsJs,
  expandOneFinal as expandOneFinalJs,
  exampleCharForFinal as exampleCharForFinalJs,
  finalsCompatible as finalsCompatibleJs,
  formatFinalWithExample as formatFinalWithExampleJs,
  isRhymeProfile as isRhymeProfileJs,
  normalizeRhymeProfile as normalizeRhymeProfileJs,
  rhymeClassesForProfile as rhymeClassesForProfileJs,
  rhymeGroupsForProfile as rhymeGroupsForProfileJs,
  rhymeProfileGuideOrder as rhymeProfileGuideOrderJs,
  RHYME_PROFILE_LABELS as LABELS,
  RHYME_PROFILES as PROFILES,
} from '../../../shared/rhyme-match-profile.mjs';

export type RhymeProfile = 'exact' | 'tong' | 'nucleus' | 'coda';

export type RhymeClass = {
  readonly name: string;
  readonly finals: readonly string[];
};

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

export function rhymeClassesForProfile(profile: RhymeProfile | string): readonly RhymeClass[] {
  return rhymeClassesForProfileJs(profile) as readonly RhymeClass[];
}

export function rhymeGroupsForProfile(profile: RhymeProfile | string): readonly (readonly string[])[] {
  return rhymeGroupsForProfileJs(profile) as readonly (readonly string[])[];
}

export function rhymeProfileGuideOrder(): readonly RhymeProfile[] {
  return rhymeProfileGuideOrderJs() as readonly RhymeProfile[];
}

export function exampleCharForFinal(final: string): string {
  return exampleCharForFinalJs(final);
}

export function formatFinalWithExample(final: string): string {
  return formatFinalWithExampleJs(final);
}
