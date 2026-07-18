/**
 * Workbench POS filter — 專案自建詞性 formal set.
 * Rule: keep when seed∩cand formal POS nonempty; no seed POS → keep all;
 * candidate missing POS → keep (詞性缺標唔罰).
 */
import { FORMAL_POS } from '../pos/types.ts';

export type ProjectPosCode = 'n' | 'v' | 'a' | 'r' | 'x' | 'u';

/** @deprecated COW four-bucket alias; prefer ProjectPosCode */
export type CowPos = 'n' | 'v' | 'a' | 'r';

export function samePosBucket(seedPos: ReadonlySet<string>, candPos: ReadonlySet<string>): boolean {
  if (seedPos.size === 0) return true;
  if (candPos.size === 0) return true;
  for (const p of seedPos) {
    if (candPos.has(p)) return true;
  }
  return false;
}

export function filterLiteralsBySeedPos(
  seed: string,
  candidates: readonly string[],
  posMap: ReadonlyMap<string, ReadonlySet<string>>,
): string[] {
  const seedPos = posMap.get(seed) ?? new Set<string>();
  return candidates.filter((c) => samePosBucket(seedPos, posMap.get(c) ?? new Set()));
}

/** Filter candidate objects by formal POS map (缺標 keep). */
export function filterCandidatesBySeedPos<T extends { literal: string }>(
  seedLiteral: string,
  candidates: readonly T[],
  posMap: ReadonlyMap<string, ReadonlySet<string>>,
): T[] {
  const seedPos = posMap.get(seedLiteral) ?? new Set<string>();
  if (seedPos.size === 0) return [...candidates];
  return candidates.filter((c) => samePosBucket(seedPos, posMap.get(c.literal) ?? new Set()));
}

export function onlyFormalPos(codes: Iterable<string>): Set<string> {
  const out = new Set<string>();
  for (const c of codes) {
    if (FORMAL_POS.has(c)) out.add(c);
  }
  return out;
}

export const POS_LABEL_ZH: Record<ProjectPosCode, string> = {
  n: '名',
  v: '動',
  a: '形',
  r: '副',
  x: '虛',
  u: '未定',
};

/** @deprecated use POS_LABEL_ZH */
export const COW_POS_LABEL: Record<CowPos, string> = {
  n: '名',
  v: '動',
  a: '形',
  r: '副',
};
