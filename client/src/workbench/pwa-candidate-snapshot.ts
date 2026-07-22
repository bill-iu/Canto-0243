import type { DatabaseBackend, DatabaseStatement } from '../db/database-backend.ts';
import { yieldToMainThread } from '../db/search-cancel.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from './contracts.ts';
import { candidateSnapshotIdentity } from './candidate-snapshot-identity.ts';
import {
  buildReplacementSnapshot,
  pageReplacementSnapshot,
  type PlannerDeps,
  type ReplacementSnapshot,
} from './plan-replacements.ts';

function abortError(): DOMException {
  return new DOMException('Aborted', 'AbortError');
}

function yieldingDatabase(db: DatabaseBackend): DatabaseBackend {
  if (typeof window === 'undefined') return db;
  return {
    async prepare(sql): Promise<DatabaseStatement> {
      const statement = await db.prepare(sql);
      let steps = 0;
      return {
        bind: (values) => statement.bind(values),
        async step() {
          steps += 1;
          if (steps % 256 === 0) await yieldToMainThread();
          return statement.step();
        },
        getAsObject: () => statement.getAsObject(),
        reset: () => statement.reset(),
        free: () => statement.free(),
      };
    },
    close: () => db.close(),
  };
}

/** One active immutable pool per PWA workbench adapter. */
export class PwaCandidateSnapshotStore {
  private identity: string | null = null;
  private snapshot: ReplacementSnapshot | null = null;
  private building: Promise<ReplacementSnapshot> | null = null;
  private generation = 0;

  async page(
    plan: ReplacementPlanV1,
    db: DatabaseBackend,
    signal?: AbortSignal,
    deps: PlannerDeps = {},
    identitySalt = '',
  ): Promise<WorkbenchCandidateResponse> {
    const identity = `${candidateSnapshotIdentity(plan)}\0${identitySalt}`;
    if (identity !== this.identity) {
      const previousBuild = this.building;
      this.identity = identity;
      this.snapshot = null;
      this.generation += 1;
      const generation = this.generation;
      const build = () => buildReplacementSnapshot(plan, yieldingDatabase(db), {
        ...deps,
        shouldCancel: () => generation !== this.generation,
      });
      this.building = (previousBuild
        ? previousBuild.catch(() => undefined).then(build)
        : build()).then((snapshot) => {
        if (generation !== this.generation) throw abortError();
        this.snapshot = snapshot;
        return snapshot;
      }).finally(() => {
        if (generation === this.generation) this.building = null;
      });
    }
    const generation = this.generation;
    const snapshot = this.snapshot ?? await this.building;
    if (!snapshot || signal?.aborted || generation !== this.generation) throw abortError();
    return pageReplacementSnapshot(plan, snapshot);
  }
}
