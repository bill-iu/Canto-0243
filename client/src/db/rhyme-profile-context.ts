/**
 * Request-scoped 韻母比對檔 (ADR-0078).
 * Set at search / workbench entry; filters expand finals via getRhymeProfile().
 */
import {
  normalizeRhymeProfile,
  type RhymeProfile,
} from './rhyme-match-profile.ts';

let current: RhymeProfile = 'exact';

export function getRhymeProfile(): RhymeProfile {
  return current;
}

export function setRhymeProfile(profile: RhymeProfile | string | null | undefined): void {
  current = normalizeRhymeProfile(profile);
}

export function withRhymeProfile<T>(profile: RhymeProfile | string | null | undefined, fn: () => T): T {
  const prev = current;
  current = normalizeRhymeProfile(profile);
  try {
    return fn();
  } finally {
    current = prev;
  }
}

export async function withRhymeProfileAsync<T>(
  profile: RhymeProfile | string | null | undefined,
  fn: () => Promise<T>,
): Promise<T> {
  const prev = current;
  current = normalizeRhymeProfile(profile);
  try {
    return await fn();
  } finally {
    current = prev;
  }
}
