import { useEffect, useMemo, useState } from 'react';

import { filterByProjectPos, isPosFilterActive, type PosFilterState } from '../pos/filter.ts';
import type {
  CandidateGroups,
  ReplacementPlanV1,
  WorkbenchCandidate,
  WorkbenchCandidateResponse,
} from './contracts.ts';
import { WORKBENCH_CANDIDATE_PAGE_SIZE } from './contracts.ts';
import { selectWorkbenchAdapter, type WorkbenchAdapter } from './workbench-adapter.ts';

const EMPTY_CREATOR_FILTER: PosFilterState = { pos: [], family: [], voice: [] };

/** Only creator 三軸詞性篩選 — never auto-filter by seed gate POS (ADR follow-up). */
export function applyCreatorPosFilter(
  next: WorkbenchCandidateResponse,
  filter: PosFilterState,
): WorkbenchCandidateResponse {
  const apply = (groups: CandidateGroups): CandidateGroups => ({
    direct_syn: filterByProjectPos(groups.direct_syn, (row) => row.literal, filter),
    semantic_related: filterByProjectPos(groups.semantic_related, (row) => row.literal, filter),
    sound_only: filterByProjectPos(groups.sound_only, (row) => row.literal, filter),
  });
  return { ...next, exact: apply(next.exact) };
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

function emptyGroups(): CandidateGroups {
  return { direct_syn: [], semantic_related: [], sound_only: [] };
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
    const pageSize = plan.limit ?? WORKBENCH_CANDIDATE_PAGE_SIZE;
    const userOffset = plan.offset ?? 0;
    const filterOn = isPosFilterActive(posFilter);
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        if (!filterOn) {
          const next = await activeAdapter.findCandidates(plan, controller.signal);
          if (controller.signal.aborted) return;
          if (next.selectionVersion !== plan.selectionVersion) return;
          setRaw((prev) => {
            if (userOffset > 0 && prev && prev.selectionVersion === next.selectionVersion) {
              return {
                ...next,
                exact: mergeGroups(prev.exact, next.exact),
                relaxation: prev.relaxation ?? next.relaxation,
              };
            }
            return next;
          });
          return;
        }

        // POS active (ADR-0064 amend): over-fetch engine pages until filtered >= target
        // or pool exhausted. userOffset 0 → first 400 filtered; 400 → 800 filtered; …
        const targetFiltered = userOffset + pageSize;
        let engineOffset = 0;
        let acc: WorkbenchCandidateResponse | null = null;
        let total = Number.POSITIVE_INFINITY;

        while (!controller.signal.aborted) {
          const page = await activeAdapter.findCandidates(
            { ...plan, offset: engineOffset, limit: pageSize },
            controller.signal,
          );
          if (page.selectionVersion !== plan.selectionVersion) return;
          total = page.total;
          if (!acc) {
            acc = {
              ...page,
              exact: {
                direct_syn: [...page.exact.direct_syn],
                semantic_related: [...page.exact.semantic_related],
                sound_only: [...page.exact.sound_only],
              },
            };
          } else {
            acc = {
              ...page,
              exact: mergeGroups(acc.exact, page.exact),
              relaxation: acc.relaxation ?? page.relaxation,
              total: page.total,
            };
          }
          const filteredCount = groupCount(applyCreatorPosFilter(acc, posFilter).exact);
          const pageRows = groupCount(page.exact);
          engineOffset += pageSize;
          if (filteredCount >= targetFiltered) break;
          if (pageRows === 0) break;
          if (engineOffset >= total) break;
        }
        if (!controller.signal.aborted && acc) setRaw(acc);
      } catch (nextError: unknown) {
        if (!controller.signal.aborted) {
          setError(nextError instanceof Error ? nextError : new Error('candidate request failed'));
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [activeAdapter, plan, posFilter]);

  const response = useMemo(
    () => (raw ? applyCreatorPosFilter(raw, posFilter) : null),
    [raw, posFilter],
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

