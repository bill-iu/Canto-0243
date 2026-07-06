import type { DatabaseBackend, DatabaseStatement, SqlBindParams } from './database-backend.ts';
import { lexiconOpfsFileName } from './opfs-lexicon.ts';
import type { OpfsVfsWorkerRequest, OpfsVfsWorkerResponse } from './opfs-vfs-worker.ts';

type Pending = {
  resolve: (value: OpfsVfsWorkerResponse) => void;
  reject: (reason?: unknown) => void;
};

type InitResult = Extract<OpfsVfsWorkerResponse, { type: 'init-ok' }>;
type QueryResult = Extract<OpfsVfsWorkerResponse, { type: 'query-ok' }>;

class OpfsVfsBackend implements DatabaseBackend {
  private nextId = 1;
  private readonly pending = new Map<number, Pending>();
  private closed = false;
  private readonly worker: Worker;

  constructor(worker: Worker) {
    this.worker = worker;
    worker.addEventListener('message', (event: MessageEvent<OpfsVfsWorkerResponse>) => {
      const res = event.data;
      const pending = this.pending.get(res.id);
      if (!pending) {
        return;
      }
      this.pending.delete(res.id);
      if (res.type === 'error') {
        pending.reject(new Error(res.message));
        return;
      }
      pending.resolve(res);
    });
    worker.addEventListener('error', (event) => {
      this.rejectAll(event.error ?? new Error(event.message));
    });
  }

  async init(fileName: string, dbUrl: string): Promise<InitResult> {
    return this.ask({ type: 'init', fileName, dbUrl });
  }

  async prepare(sql: string): Promise<DatabaseStatement> {
    if (this.closed) {
      throw new Error('OPFS VFS database is closed');
    }
    return new OpfsVfsStatement(this, sql);
  }

  async close(): Promise<void> {
    if (this.closed) {
      return;
    }
    this.closed = true;
    try {
      await this.ask({ type: 'close' });
    } finally {
      this.worker.terminate();
      this.rejectAll(new Error('OPFS VFS database closed'));
    }
  }

  async query(sql: string, params: SqlBindParams): Promise<QueryResult> {
    return this.ask({ type: 'query', sql, params });
  }

  private ask<T extends Omit<OpfsVfsWorkerRequest, 'id'>>(msg: T): Promise<ExtractResponse<T['type']>> {
    const id = this.nextId;
    this.nextId += 1;
    const request = { ...msg, id } as OpfsVfsWorkerRequest;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {
        resolve: (value) => resolve(value as ExtractResponse<T['type']>),
        reject,
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
  T extends 'init' ? InitResult :
  T extends 'query' ? QueryResult :
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

export type OpenOpfsVfsDatabaseResult = {
  db: DatabaseBackend;
  fileName: string;
  byteSize: number;
  fetched: boolean;
};

export async function openOpfsVfsDatabase(opts: {
  version: string;
  dbUrl: string;
}): Promise<OpenOpfsVfsDatabaseResult> {
  if (typeof Worker === 'undefined') {
    throw new Error('OPFS VFS requires Worker support');
  }
  const worker = new Worker(new URL('./opfs-vfs-worker.ts', import.meta.url), { type: 'module' });
  const backend = new OpfsVfsBackend(worker);
  const fileName = lexiconOpfsFileName(opts.version);
  const init = await backend.init(fileName, opts.dbUrl);
  return {
    db: backend,
    fileName: init.fileName,
    byteSize: init.byteSize,
    fetched: init.fetched,
  };
}
