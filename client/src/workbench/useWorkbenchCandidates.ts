import { useEffect, useMemo, useState } from 'react';

import type { ReplacementPlanV1, WorkbenchCandidateResponse } from './contracts.ts';
import { selectWorkbenchAdapter, type WorkbenchAdapter } from './workbench-adapter.ts';

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
      if (next.selectionVersion === plan.selectionVersion) setResponse(next);
    }).catch((nextError: unknown) => {
      if (!controller.signal.aborted) setError(nextError instanceof Error ? nextError : new Error('candidate request failed'));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [activeAdapter, plan]);

  return { response, error, loading };
}
