import type { DatabaseBackend, DatabaseStatement, SqlBindParams } from './database-backend.ts';
import { lexiconOpfsFileName } from './opfs-lexicon.ts';
import { reportDownloadBytes } from './startup-progress.ts';
import type { OpfsVfsWorkerRequest, OpfsVfsWorkerResponse } from './opfs-vfs-worker.ts';
import type { ReplacementPlanV1, WorkbenchCandidateResponse } from '../workbench/contracts.ts';
import type { GroupPoolInput } from '../workbench/group-candidates.ts';
import {
  recordResumeDebug,
  type ResumeDebugWorkerState,
} from '../resume-debug.ts';

type Pending = {
  resolve: (value: OpfsVfsWorkerResponse) => void;
  reject: (reason?: unknown) => void;
  type: OpfsVfsWorkerRequest['type'];
  startedAt: number;
};

type InitResult = Extract<OpfsVfsWorkerResponse, { type: 'init-ok' }>;
type QueryResult = Extract<OpfsVfsWorkerResponse, { type: 'query-ok' }>;
type WorkbenchResult = Extract<OpfsVfsWorkerResponse, { type: 'workbench-ok' }>;

let sharedWorker: Worker | null = null;
let sharedBackend: OpfsVfsBackend | null = null;

class OpfsVfsBackend implements DatabaseBackend {
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private closed = false;
  private readonly worker: Worker;

  constructor(worker: Worker) {
    this.worker = worker;
    worker.addEventListener('message', (event: MessageEvent<OpfsVfsWorkerResponse>) => {
      const res = event.data;
      if (res.type === 'progress') {
        reportDownloadBytes(res.loaded, res.total);
        return;
      }
      const pending = this.pending.get(res.id);
      if (!pending) return;
      this.pending.delete(res.id);
      recordResumeDebug('worker-response', {
        id: res.id,
        requestType: pending.type,
        responseType: res.type,
        elapsedMs: Math.round(performance.now() - pending.startedAt),
        pending: this.pending.size,
      });
      if (res.type === 'error') {
        pending.reject(new Error(res.message));
        return;
      }
      pending.resolve(res);
    });
    worker.addEventListener('error', (event) => {
      recordResumeDebug('worker-error', { message: event.message });
      this.rejectAll(event.error ?? new Error(event.message));
    });
    worker.addEventListener('messageerror', () => {
      recordResumeDebug('worker-message-error', { pending: this.pending.size });
    });
  }

  async prewarm(): Promise<void> {
    void this.ask({ type: 'prewarm' });
  }

  async init(
    fileName: string,
    dbUrl: string,
    opts?: { gzip?: boolean; progressTotal?: number; expectedByteSize?: number },
  ): Promise<InitResult> {
    return this.ask({
      type: 'init',
      fileName,
      dbUrl,
      gzip: opts?.gzip,
      progressTotal: opts?.progressTotal,
      expectedByteSize: opts?.expectedByteSize,
    });
  }

  async prepare(sql: string): Promise<DatabaseStatement> {
    if (this.closed) throw new Error('OPFS VFS database is closed');
    return new OpfsVfsStatement(this, sql);
  }

  async close(): Promise<void> {
    if (this.closed) return;
    this.closed = true;
    try {
      await this.ask({ type: 'close' });
    } finally {
      this.rejectAll(new Error('OPFS VFS database closed'));
    }
  }

  async query(sql: string, params: SqlBindParams): Promise<QueryResult> {
    return this.ask({ type: 'query', sql, params });
  }

  async workbench(
    plan: ReplacementPlanV1,
    pool: GroupPoolInput,
    identitySalt: string,
  ): Promise<WorkbenchResult> {
    return this.ask({ type: 'workbench', plan, pool, identitySalt });
  }

  debugState(): ResumeDebugWorkerState {
    const now = performance.now();
    return {
      exists: true,
      pending: [...this.pending.entries()].map(([id, request]) => ({
        id,
        type: request.type,
        ageMs: Math.round(now - request.startedAt),
      })),
    };
  }

  private ask<T extends Omit<OpfsVfsWorkerRequest, 'id'>>(msg: T): Promise<ExtractResponse<T['type']>> {
    const id = this.nextId;
    this.nextId += 1;
    const request = { ...msg, id } as OpfsVfsWorkerRequest;
    return new Promise((resolve, reject) => {
      const startedAt = performance.now();
      this.pending.set(id, {
        resolve: (value) => resolve(value as ExtractResponse<T['type']>),
        reject,
        type: request.type,
        startedAt,
      });
      recordResumeDebug('worker-request', {
        id,
        requestType: request.type,
        pending: this.pending.size,
      });
      this.worker.postMessage(request);
    });
  }

  private rejectAll(reason: unknown): void {
    for (const pending of this.pending.values()) {
      pending.reject(reason);
    }
    this.pending.clear();
  }
}

type ExtractResponse<T extends OpfsVfsWorkerRequest['type']> =
  T extends 'prewarm' ? Extract<OpfsVfsWorkerResponse, { type: 'prewarm-ok' }> :
  T extends 'init' ? InitResult :
  T extends 'query' ? QueryResult :
  T extends 'workbench' ? WorkbenchResult :
  Extract<OpfsVfsWorkerResponse, { type: 'close-ok' }>;

class OpfsVfsStatement implements DatabaseStatement {
  private params: SqlBindParams = [];
  private rows: Array<Record<string, unknown>> | null = null;
  private index = -1;
  private readonly backend: OpfsVfsBackend;
  private readonly sql: string;

  constructor(backend: OpfsVfsBackend, sql: string) {
    this.backend = backend;
    this.sql = sql;
  }

  async bind(values: SqlBindParams = []): Promise<void> {
    this.params = values;
    this.rows = null;
    this.index = -1;
  }

  async step(): Promise<boolean> {
    if (!this.rows) {
      const result = await this.backend.query(this.sql, this.params);
      this.rows = result.rows;
      this.index = -1;
    }
    this.index += 1;
    return this.index < this.rows.length;
  }

  async getAsObject(): Promise<Record<string, unknown>> {
    const row = this.rows?.[this.index];
    return row ? { ...row } : {};
  }

  async reset(): Promise<void> {
    this.rows = null;
    this.index = -1;
  }

  async free(): Promise<void> {
    this.rows = [];
    this.index = -1;
  }
}

function getSharedBackend(): OpfsVfsBackend {
  if (typeof Worker === 'undefined') {
    throw new Error('OPFS VFS requires Worker support');
  }
  if (!sharedBackend) {
    sharedWorker = new Worker(new URL('./opfs-vfs-worker.ts', import.meta.url), { type: 'module' });
    sharedBackend = new OpfsVfsBackend(sharedWorker);
    recordResumeDebug('worker-created');
  }
  return sharedBackend;
}

/** E: 下載前預熱 wa-sqlite + OPFS VFS */
export function prewarmOpfsVfsWorker(): void {
  try {
    void getSharedBackend().prewarm();
  } catch {
    /* ponytail: prewarm best-effort */
  }
}

export type OpenOpfsVfsDatabaseResult = {
  db: DatabaseBackend;
  fileName: string;
  byteSize: number;
  fetched: boolean;
};

export function resetOpfsVfsWorker(): void {
  if (sharedWorker) {
    recordResumeDebug('worker-reset');
    sharedWorker.terminate();
    sharedWorker = null;
    sharedBackend = null;
  }
}

export function getOpfsVfsWorkerDebugState(): ResumeDebugWorkerState {
  return sharedBackend?.debugState() ?? { exists: false, pending: [] };
}

export function isOpfsVfsBackend(db: DatabaseBackend): boolean {
  return db === sharedBackend;
}

export async function requestOpfsWorkbenchPage(
  db: DatabaseBackend,
  plan: ReplacementPlanV1,
  pool: GroupPoolInput,
  identitySalt: string,
  signal?: AbortSignal,
): Promise<WorkbenchCandidateResponse> {
  if (!sharedBackend || db !== sharedBackend) {
    throw new Error('workbench worker requires the active OPFS VFS backend');
  }
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  const request = sharedBackend.workbench(plan, pool, identitySalt);
  if (!signal) return (await request).response;
  const aborted = new Promise<never>((_resolve, reject) => {
    signal.addEventListener(
      'abort',
      () => reject(new DOMException('Aborted', 'AbortError')),
      { once: true },
    );
  });
  return (await Promise.race([request, aborted])).response;
}

export async function openOpfsVfsDatabase(opts: {
  version: string;
  fetchUrl: string;
  gzip?: boolean;
  progressTotal?: number;
  expectedByteSize?: number;
}): Promise<OpenOpfsVfsDatabaseResult> {
  const backend = getSharedBackend();
  const fileName = lexiconOpfsFileName(opts.version);
  const init = await backend.init(fileName, opts.fetchUrl, {
    gzip: opts.gzip,
    progressTotal: opts.progressTotal,
    expectedByteSize: opts.expectedByteSize,
  });
  return {
    db: backend,
    fileName: init.fileName,
    byteSize: init.byteSize,
    fetched: init.fetched,
  };
}
