import type { DatabaseBackend, DatabaseStatement, SqlBindParams } from './database-backend.ts';
import { lexiconOpfsFileName } from './opfs-lexicon.ts';
import { reportDownloadBytes } from './startup-progress.ts';
import { storageError } from './storage-error.ts';
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

let sharedBackend: OpfsVfsBackend | null = null;

class OpfsVfsBackend implements DatabaseBackend {
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private closed = false;
  private closing: Promise<void> | null = null;
  private readonly worker: Worker;

  constructor(worker: Worker) {
    this.worker = worker;
    worker.addEventListener('message', (event: MessageEvent<OpfsVfsWorkerResponse>) => {
      const res = event.data;
      if (res.type === 'progress') {
        if (this.closed) return;
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
        recordResumeDebug('worker-failure', { name: res.name, stage: res.stage, fileName: res.fileName ?? null });
        pending.reject(storageError(res, res.stage));
        return;
      }
      pending.resolve(res);
    });
    worker.addEventListener('error', (event) => {
      recordResumeDebug('worker-error', { message: event.message });
      this.rejectAll(event.error ?? new Error(event.message));
      this.terminate();
    });
    worker.addEventListener('messageerror', () => {
      recordResumeDebug('worker-message-error', { pending: this.pending.size });
      this.rejectAll(storageError(new Error('Cannot decode Worker response'), 'worker-message'));
      this.terminate();
    });
  }

  async prewarm(): Promise<void> {
    await this.ask({ type: 'prewarm' });
  }

  async init(
    fileName: string,
    dbUrl: string,
    opts?: { gzip?: boolean; progressTotal?: number; expectedByteSize?: number; expectedSha256?: string },
  ): Promise<InitResult> {
    return this.ask({
      type: 'init',
      fileName,
      dbUrl,
      gzip: opts?.gzip,
      progressTotal: opts?.progressTotal,
      expectedByteSize: opts?.expectedByteSize,
      expectedSha256: opts?.expectedSha256,
    });
  }

  async prepare(sql: string): Promise<DatabaseStatement> {
    if (this.closed) throw new Error('OPFS VFS database is closed');
    return new OpfsVfsStatement(this, sql);
  }

  close(): Promise<void> {
    if (this.closing) return this.closing;
    if (this.closed) return Promise.resolve();
    this.closed = true;
    this.rejectAll(new DOMException('OPFS VFS database closed', 'AbortError'));
    this.closing = (async () => {
      let timer: ReturnType<typeof setTimeout> | undefined;
      try {
        await Promise.race([
          this.ask({ type: 'close' }),
          new Promise<void>(resolve => { timer = setTimeout(resolve, 1500); }),
        ]);
      } catch { /* termination releases resources even if graceful close fails */ }
      finally { clearTimeout(timer); this.terminate(); }
    })();
    return this.closing;
  }

  private terminate(): void {
    this.closed = true;
    this.rejectAll(new DOMException('OPFS VFS Worker terminated', 'AbortError'));
    this.worker.terminate();
    if (sharedBackend === this) { sharedBackend = null; }
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
    if (this.closed && msg.type !== 'close') return Promise.reject(new DOMException('OPFS VFS database closed', 'AbortError'));
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
      try { this.worker.postMessage(request); }
      catch (error) { this.pending.delete(id); reject(error); }
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
    const worker = new Worker(new URL('./opfs-vfs-worker.ts', import.meta.url), { type: 'module' });
    sharedBackend = new OpfsVfsBackend(worker);
    recordResumeDebug('worker-created');
  }
  return sharedBackend;
}

/** E: 下載前預熱 wa-sqlite + OPFS VFS */
export function prewarmOpfsVfsWorker(): void {
  try {
    void getSharedBackend().prewarm().catch(error => console.warn('OPFS prewarm failed:', error));
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

export async function resetOpfsVfsWorker(): Promise<void> {
  const backend = sharedBackend;
  sharedBackend = null;
  if (backend) { recordResumeDebug('worker-reset'); await backend.close(); }
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
  expectedSha256?: string;
}): Promise<OpenOpfsVfsDatabaseResult> {
  const backend = getSharedBackend();
  const fileName = lexiconOpfsFileName(opts.version);
  const init = await backend.init(fileName, opts.fetchUrl, {
    gzip: opts.gzip,
    progressTotal: opts.progressTotal,
    expectedByteSize: opts.expectedByteSize,
    expectedSha256: opts.expectedSha256,
  });
  return {
    db: backend,
    fileName: init.fileName,
    byteSize: init.byteSize,
    fetched: init.fetched,
  };
}
