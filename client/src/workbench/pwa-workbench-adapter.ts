import { getDatabase } from '../db/init.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';
import { WorkbenchAdapterError } from './workbench-adapter.ts';
import { resolvePwaLineReadings } from './pwa-line-readings.ts';
import { planPwaReplacements } from './pwa-replacement-planner.ts';

export function createPwaWorkbenchAdapter(): WorkbenchAdapter {
  const database = () => {
    try {
      return getDatabase();
    } catch {
      throw new WorkbenchAdapterError('not_ready', 'lexicon not ready');
    }
  };
  return {
    resolveLine(input, signal) {
      if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
      return resolvePwaLineReadings(input, database());
    },
    findCandidates(plan, signal) {
      if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
      return planPwaReplacements(plan, database());
    },
  };
}
