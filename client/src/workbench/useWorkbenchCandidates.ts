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

export function useWorkbenchCandidates(
  plan: ReplacementPlanV1 | null,
  adapter?: WorkbenchAdapter,
  posFilter: PosFilterState = EMPTY_CREATOR_FILTER,
) {
  const defaultAdapter = useMemo(() => selectWorkbenchAdapter(), []);
  const activeAdapter = adapter ?? defaultAdapter;
  const [response, setResponse] = useState<WorkbenchCandidateResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!plan) {
      setResponse(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void activeAdapter.findCandidates(plan, controller.signal).then((next) => {
      if (next.selectionVersion === plan.selectionVersion) {
        setResponse(applyPosFilter(plan, next, posFilter));
      }
    }).catch((nextError: unknown) => {
      if (!controller.signal.aborted) setError(nextError instanceof Error ? nextError : new Error('candidate request failed'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [activeAdapter, plan, posFilter]);

  return { response, error, loading };
}
