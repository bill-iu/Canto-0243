import { useEffect, useMemo, useState } from 'react';

import { formalPosMap, isProjectPosReady } from '../pos/carrier.ts';
import { filterByProjectPos, type PosFilterState } from '../pos/filter.ts';
import type {
  CandidateGroups,
  ReplacementPlanV1,
  WorkbenchCandidate,
  WorkbenchCandidateResponse,
} from './contracts.ts';
import { filterCandidatesBySeedPos } from './pos-meta.ts';
import { selectWorkbenchAdapter, type WorkbenchAdapter } from './workbench-adapter.ts';

const EMPTY_CREATOR_FILTER: PosFilterState = { pos: [], family: [], voice: [] };

function filterGroups(seed: string, groups: CandidateGroups, map: ReadonlyMap<string, ReadonlySet<string>>): CandidateGroups {
  const f = (xs: WorkbenchCandidate[]) => filterCandidatesBySeedPos(seed, xs, map);
  return {
    direct_syn: f(groups.direct_syn),
    semantic_related: f(groups.semantic_related),
    sound_only: f(groups.sound_only),
  };
}

function applyPosFilter(plan: ReplacementPlanV1, next: WorkbenchCandidateResponse, filter: PosFilterState): WorkbenchCandidateResponse {
  let exact = next.exact;
  if (isProjectPosReady() && plan.semanticSeed) {
    const map = formalPosMap();
    if (map.size) exact = filterGroups(plan.semanticSeed, exact, map);
  }
  const applyCreatorFilter = (groups: CandidateGroups): CandidateGroups => ({
    direct_syn: filterByProjectPos(groups.direct_syn, (row) => row.literal, filter),
    semantic_related: filterByProjectPos(groups.semantic_related, (row) => row.literal, filter),
    sound_only: filterByProjectPos(groups.sound_only, (row) => row.literal, filter),
  });
  return {
    ...next,
    exact: applyCreatorFilter(exact),
  };
}

function candidateKey(c: WorkbenchCandidate): string {
  return `${c.literal}\0${c.jyutping}`;
}

function mergeGroups(prev: CandidateGroups, next: CandidateGroups): CandidateGroups {
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

function groupCount(groups: CandidateGroups): number {
  return groups.direct_syn.length + groups.semantic_related.length + groups.sound_only.length;
}

export function useWorkbenchCandidates(
  plan: ReplacementPlanV1 | null,
  adapter?: WorkbenchAdapter,
  posFilter: PosFilterState = EMPTY_CREATOR_FILTER,
) {
  const defaultAdapter = useMemo(() => selectWorkbenchAdapter(), []);
  const activeAdapter = adapter ?? defaultAdapter;
  const [raw, setRaw] = useState<WorkbenchCandidateResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!plan) {
      setRaw(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    const offset = plan.offset ?? 0;
    setLoading(true);
    setError(null);
    void activeAdapter.findCandidates(plan, controller.signal).then((next) => {
      if (next.selectionVersion !== plan.selectionVersion) return;
      setRaw((prev) => {
        if (offset > 0 && prev && prev.selectionVersion === next.selectionVersion) {
          return {
            ...next,
            exact: mergeGroups(prev.exact, next.exact),
            relaxation: prev.relaxation ?? next.relaxation,
          };
        }
        return next;
      });
    }).catch((nextError: unknown) => {
      if (!controller.signal.aborted) setError(nextError instanceof Error ? nextError : new Error('candidate request failed'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [activeAdapter, plan]);

  const response = useMemo(
    () => (raw && plan ? applyPosFilter(plan, raw, posFilter) : null),
    [raw, plan, posFilter],
  );

  return {
    response,
    error,
    loading,
    loadedCount: response ? groupCount(response.exact) : 0,
    /** Engine rows accumulated (before creator POS filter). */
    fetchedCount: raw ? groupCount(raw.exact) : 0,
  };
}
