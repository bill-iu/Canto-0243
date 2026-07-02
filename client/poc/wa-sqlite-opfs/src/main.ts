import type { WorkerRequest, WorkerResponse } from './db-worker.ts';

const logEl = document.getElementById('log')!;
const envEl = document.getElementById('env')!;
const sourceEl = document.getElementById('db-source') as HTMLSelectElement;

function log(line: string, kind: 'ok' | 'err' | '' = '') {
  const prefix = kind === 'ok' ? '✓ ' : kind === 'err' ? '✗ ' : '';
  logEl.textContent = `${prefix}${line}\n${logEl.textContent}`.trim();
  logEl.className = kind;
}

function envSummary(): string {
  const opfs = typeof navigator.storage?.getDirectory === 'function';
  const sab = typeof SharedArrayBuffer !== 'undefined';
  const ua = navigator.userAgent;
  return `OPFS=${opfs ? 'yes' : 'no'} | SharedArrayBuffer=${sab ? 'yes' : 'no'} | ${ua}`;
}

envEl.textContent = envSummary();

const worker = new Worker(new URL('./db-worker.ts', import.meta.url), { type: 'module' });

function ask(req: WorkerRequest): Promise<WorkerResponse> {
  return new Promise((resolve, reject) => {
    const onMessage = (event: MessageEvent<WorkerResponse>) => {
      worker.removeEventListener('message', onMessage);
      worker.removeEventListener('error', onError);
      resolve(event.data);
    };
    const onError = (event: ErrorEvent) => {
      worker.removeEventListener('message', onMessage);
      worker.removeEventListener('error', onError);
      reject(event.error ?? new Error(event.message));
    };
    worker.addEventListener('message', onMessage);
    worker.addEventListener('error', onError);
    worker.postMessage(req);
  });
}

async function fetchDb(url: string): Promise<Uint8Array> {
  log(`fetch ${url} …`);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`fetch ${url} → ${res.status}`);
  }
  return new Uint8Array(await res.arrayBuffer());
}

document.getElementById('btn-import')!.addEventListener('click', async () => {
  try {
    const url = sourceEl.value;
    const bytes = await fetchDb(url);
    log(`import ${bytes.byteLength} bytes → OPFS …`);
    const res = await ask({ type: 'import-and-count', bytes });
    if (res.type === 'error') {
      throw new Error(res.message);
    }
    log(
      `COUNT(*) = ${res.count} (vfs=${res.vfs}, file=${res.dbFile}, imported=${res.importedBytes})`,
      'ok',
    );
  } catch (e) {
    log(e instanceof Error ? e.message : String(e), 'err');
  }
});

document.getElementById('btn-count')!.addEventListener('click', async () => {
  try {
    log('COUNT from OPFS only (no fetch) …');
    const res = await ask({ type: 'count-only' });
    if (res.type === 'error') {
      throw new Error(res.message);
    }
    log(`COUNT(*) = ${res.count} (no re-fetch)`, 'ok');
  } catch (e) {
    log(e instanceof Error ? e.message : String(e), 'err');
  }
});

document.getElementById('btn-reset')!.addEventListener('click', async () => {
  try {
    await ask({ type: 'reset' });
    log('OPFS db removed', 'ok');
  } catch (e) {
    log(e instanceof Error ? e.message : String(e), 'err');
  }
});
