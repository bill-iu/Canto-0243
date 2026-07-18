import { useEffect, useMemo, useState } from 'react';

import { formalPosMap, isProjectPosReady } from '../pos/carrier.ts';
import type {
  CandidateGroups,
  ReplacementPlanV1,
  WorkbenchCandidate,
  WorkbenchCandidateResponse,
} from './contracts.ts';
import { filterCandidatesBySeedPos } from './pos-meta.ts';
import { selectWorkbenchAdapter, type WorkbenchAdapter } from './workbench-adapter.ts';

function filterGroups(seed: string, groups: CandidateGroups, map: ReadonlyMap<string, ReadonlySet<string>>): CandidateGroups {
  const f = (xs: WorkbenchCandidate[]) => filterCandidatesBySeedPos(seed, xs, map);
  return {
    direct_syn: f(groups.direct_syn),
    semantic_related: f(groups.semantic_related),
    sound_only: f(groups.sound_only),
  };
}

function applyPosFilter(plan: ReplacementPlanV1, next: WorkbenchCandidateResponse): WorkbenchCandidateResponse {
  if (!isProjectPosReady() || !plan.semanticSeed) return next;
  const map = formalPosMap();
  if (map.size === 0) return next;
  return {
    ...next,
    exact: filterGroups(plan.semanticSeed, next.exact, map),
  };
}

export function useWorkbenchCandidates(
  plan: ReplacementPlanV1 | null,
  adapter?: WorkbenchAdapter,
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
        setResponse(applyPosFilter(plan, next));
      }
    }).catch((nextError: unknown) => {
      if (!controller.signal.aborted) setError(nextError instanceof Error ? nextError : new Error('candidate request failed'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [activeAdapter, plan]);

  return { response, error, loading };
}
