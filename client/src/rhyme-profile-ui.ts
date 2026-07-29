/**
 * Session UI state for 韻母比對檔 (ADR-0078 P1).
 * Shared by search shell + workbench; hard refresh resets to exact.
 */
import { useSyncExternalStore } from 'react';
import {
  normalizeRhymeProfile,
  type RhymeProfile,
  RHYME_PROFILE_LABELS,
  RHYME_PROFILES,
} from './db/rhyme-match-profile.ts';

export type { RhymeProfile };
export { RHYME_PROFILE_LABELS, RHYME_PROFILES, normalizeRhymeProfile };

let current: RhymeProfile = 'exact';
const listeners = new Set<() => void>();

function emit(): void {
  for (const l of listeners) l();
}

export function getUiRhymeProfile(): RhymeProfile {
  return current;
}

export function setUiRhymeProfile(profile: RhymeProfile | string): void {
  const next = normalizeRhymeProfile(profile);
  if (next === current) return;
  current = next;
  emit();
}

export function subscribeUiRhymeProfile(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useUiRhymeProfile(): [RhymeProfile, (p: RhymeProfile) => void] {
  const profile = useSyncExternalStore(subscribeUiRhymeProfile, getUiRhymeProfile, getUiRhymeProfile);
  return [profile, setUiRhymeProfile];
}
