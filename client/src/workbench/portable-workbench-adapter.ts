import { parseWorkbenchCandidateResponse, type ReplacementPlanV1 } from './contracts.ts';
import type { WorkbenchAdapter, WorkbenchAdapterOptions } from './workbench-adapter.ts';
import { WorkbenchAdapterError } from './workbench-adapter.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';
import { candidateSnapshotIdentity } from './candidate-snapshot-identity.ts';
import { createLineReadingResolver } from './line-reading-cache.ts';
import {
  markSnapshotRestarted,
  snapshotWasRestarted,
  type CandidatePageResponse,
} from './candidate-page.ts';

type FetchLike = typeof fetch;
type CandidateRequestResult = {
  page: CandidatePageResponse;
  snapshotId: string | null;
};

function mapStatus(status: number): WorkbenchAdapterError {
  if (status === 503) return new WorkbenchAdapterError('not_ready', 'lexicon not ready');
  if (status === 422) return new WorkbenchAdapterError('invalid_plan', 'invalid workbench plan');
  return new WorkbenchAdapterError('network', `workbench request failed (${status})`);
}

async function post(
  fetcher: FetchLike,
  path: string,
  body: unknown,
  signal?: AbortSignal,
  headers: Record<string, string> = {},
): Promise<{ body: unknown; response: Response }> {
  let response: Response;
  try {
    response = await fetcher(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new WorkbenchAdapterError('network', error instanceof Error ? error.message : 'network error');
  }
  if (!response.ok) throw mapStatus(response.status);
  return { body: await response.json(), response };
}

function waitForCaller<T>(promise: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
  return new Promise((resolve, reject) => {
    const aborted = () => reject(new DOMException('Aborted', 'AbortError'));
    signal.addEventListener('abort', aborted, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener('abort', aborted);
        resolve(value);
      },
      (error) => {
        signal.removeEventListener('abort', aborted);
        reject(error);
      },
    );
  });
}

function rebindPage(
  source: CandidatePageResponse,
  plan: ReplacementPlanV1,
): CandidatePageResponse {
  const page: CandidatePageResponse = {
    ...source,
    selectionVersion: plan.selectionVersion,
    relaxation: source.relaxation == null ? source.relaxation : {
      ...source.relaxation,
      plan: { ...source.relaxation.plan, selectionVersion: plan.selectionVersion },
    },
  };
  return snapshotWasRestarted(source) ? markSnapshotRestarted(page) : page;
}

export function createPortableWorkbenchAdapter(
  fetcher: FetchLike = fetch,
  options: WorkbenchAdapterOptions = {},
): WorkbenchAdapter {
  let activeIdentity: string | null = null;
  let snapshotId: string | null = null;
  let activeController: AbortController | null = null;
  let building: { identity: string; promise: Promise<CandidateRequestResult> } | null = null;
  const lineReadings = createLineReadingResolver(
    options.lexiconIdentity ?? 'dev',
    async (input, signal) => (
      await post(fetcher, '/workbench/readings', { surface: input }, signal)
    ).body as PwaLineReadingSlot[],
    options.lineReadingCacheSize,
  );

  const requestCandidates = (
    plan: ReplacementPlanV1,
    identity: string,
    requestSnapshotId: string | null,
  ): Promise<CandidateRequestResult> => {
    activeController ??= new AbortController();
    const request = post(
      fetcher,
      '/workbench/candidates',
      plan,
      activeController.signal,
      requestSnapshotId ? { 'X-Workbench-Snapshot': requestSnapshotId } : {},
    ).then((result) => {
      const parsed = parseWorkbenchCandidateResponse(result.body);
      const page = result.response.headers.get('X-Workbench-Snapshot-Rebuilt') === '1'
        ? markSnapshotRestarted(parsed)
        : parsed;
      return {
        page,
        snapshotId: result.response.headers.get('X-Workbench-Snapshot'),
      };
    });
    if ((plan.offset ?? 0) === 0 && snapshotId == null) {
      building = { identity, promise: request };
      void request.finally(() => {
        if (building?.promise === request) building = null;
      }).catch(() => {});
    }
    return request;
  };

  return {
    resolveLine(input, signal) {
      return lineReadings.resolve(input, signal);
    },
    async findCandidates(plan: ReplacementPlanV1, signal) {
      const identity = candidateSnapshotIdentity(plan);
      const requestSnapshotId = snapshotId;
      if (identity !== activeIdentity) {
        activeController?.abort();
        activeController = new AbortController();
        activeIdentity = identity;
        snapshotId = null;
        building = null;
      }
      const canCoalesce = (plan.offset ?? 0) === 0
        && snapshotId == null
        && building?.identity === identity;
      const result = await waitForCaller(
        canCoalesce
          ? building!.promise
          : requestCandidates(plan, identity, requestSnapshotId),
        signal,
      );
      if (activeIdentity === identity) {
        snapshotId = result.snapshotId;
      }
      return rebindPage(result.page, plan);
    },
  };
}
