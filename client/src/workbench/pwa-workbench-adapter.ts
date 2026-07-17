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
      try {
        return resolvePwaLineReadings(input, database());
      } catch (error) {
        // getDatabase() 係同步 throw；要變 reject 先畀 hook 嘅 .catch 接住，唔好炸 React
        return Promise.reject(error);
      }
    },
    findCandidates(plan, signal) {
      if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
      try {
        return planPwaReplacements(plan, database());
      } catch (error) {
        return Promise.reject(error);
      }
    },
  };
}
