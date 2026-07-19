import { parseWorkbenchCandidateResponse, type ReplacementPlanV1 } from './contracts.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';
import { WorkbenchAdapterError } from './workbench-adapter.ts';
import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

type FetchLike = typeof fetch;

function mapStatus(status: number): WorkbenchAdapterError {
  if (status === 503) return new WorkbenchAdapterError('not_ready', 'lexicon not ready');
  if (status === 422) return new WorkbenchAdapterError('invalid_plan', 'invalid workbench plan');
  return new WorkbenchAdapterError('network', `workbench request failed (${status})`);
}

async function post(fetcher: FetchLike, path: string, body: unknown, signal?: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetcher(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new WorkbenchAdapterError('network', error instanceof Error ? error.message : 'network error');
  }
  if (!response.ok) throw mapStatus(response.status);
  return response.json();
}

export function createPortableWorkbenchAdapter(fetcher: FetchLike = fetch): WorkbenchAdapter {
  return {
    async resolveLine(input, signal) {
      return await post(fetcher, '/workbench/readings', { surface: input }, signal) as PwaLineReadingSlot[];
    },
    async findCandidates(plan: ReplacementPlanV1, signal) {
      return parseWorkbenchCandidateResponse(await post(fetcher, '/workbench/candidates', plan, signal));
    },
  };
}
