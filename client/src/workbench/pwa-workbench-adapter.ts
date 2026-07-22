import { getDatabase } from '../db/init.ts';
import type { DatabaseBackend } from '../db/database-backend.ts';
import { isOpfsVfsBackend, requestOpfsWorkbenchPage } from '../db/opfs-vfs-backend.ts';
import { projectRelationPool } from '../db/relation-pool/index.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';
import { WorkbenchAdapterError } from './workbench-adapter.ts';
import { resolvePwaLineReadings } from './pwa-line-readings.ts';
import { PwaCandidateSnapshotStore } from './pwa-candidate-snapshot.ts';
import type { GroupPoolInput } from './group-candidates.ts';
import type { ReplacementPlanV1 } from './contracts.ts';

async function projectCompactPool(
  plan: ReplacementPlanV1,
  db: DatabaseBackend,
): Promise<GroupPoolInput> {
  if (plan.semanticIntent === 'off' || !plan.semanticSeed) return null;
  const pool = await projectRelationPool(db, plan.semanticSeed);
  const compact = (rows: Array<{ char: string; source?: string }>) => rows.map((item) => ({
    char: item.char,
    source: item.source,
  }));
  return { syns: compact(pool.syns), semantic: compact(pool.semantic) };
}

export function createPwaWorkbenchAdapter(): WorkbenchAdapter {
  const snapshots = new PwaCandidateSnapshotStore();
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
    async findCandidates(plan, signal) {
      if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
      try {
        const db = database();
        if (isOpfsVfsBackend(db)) {
          const pool = await projectCompactPool(plan, db);
          if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
          const identitySalt = JSON.stringify(pool);
          return requestOpfsWorkbenchPage(db, plan, pool, identitySalt, signal);
        }
        return snapshots.page(plan, db, signal);
      } catch (error) {
        return Promise.reject(error);
      }
    },
  };
}
