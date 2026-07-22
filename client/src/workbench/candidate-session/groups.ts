import type { PosFilterState } from '../../pos/filter.ts';
import { filterByProjectPos, isPosFilterActive } from '../../pos/filter.ts';
import type {
  CandidateGroups,
  WorkbenchCandidate,
  WorkbenchCandidateResponse,
} from '../contracts.ts';

export function emptyGroups(): CandidateGroups {
  return { direct_syn: [], semantic_related: [], sound_only: [] };
}

export function groupCount(groups: CandidateGroups): number {
  return groups.direct_syn.length + groups.semantic_related.length + groups.sound_only.length;
}

function candidateKey(c: WorkbenchCandidate): string {
  return `${c.literal}\0${c.jyutping}`;
}

export function mergeGroups(prev: CandidateGroups, next: CandidateGroups): CandidateGroups {
  const merge = (a: WorkbenchCandidate[], b: WorkbenchCandidate[]) => {
    const seen = new Set(a.map(candidateKey));
    return [...a, ...b.filter((c) => !seen.has(candidateKey(c)))];
  };
  return {
    direct_syn: merge(prev.direct_syn, next.direct_syn),
    semantic_related: merge(prev.semantic_related, next.semantic_related),
    sound_only: merge(prev.sound_only, next.sound_only),
  };
}

/** Only creator 三軸詞性篩選 — never auto-filter by seed gate POS. */
export function applyCreatorPosFilter(
  next: WorkbenchCandidateResponse,
  filter: PosFilterState,
): WorkbenchCandidateResponse {
  if (!isPosFilterActive(filter)) return next;
  const exact: CandidateGroups = {
    direct_syn: filterByProjectPos(next.exact.direct_syn, (row) => row.literal, filter),
    semantic_related: filterByProjectPos(next.exact.semantic_related, (row) => row.literal, filter),
    sound_only: filterByProjectPos(next.exact.sound_only, (row) => row.literal, filter),
  };
  const filteredCount = exact.direct_syn.length + exact.semantic_related.length + exact.sound_only.length;
  return {
    ...next,
    exact,
    relaxation: filteredCount === 0 && engineTotalOf(next) > 0 ? null : next.relaxation,
  };
}

export function engineTotalOf(response: WorkbenchCandidateResponse): number {
  return response.engineTotal ?? response.total;
}
