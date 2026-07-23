import type { PwaLineReadingSlot } from './pwa-line-readings.ts';

type LineLoader = (
  surface: string,
  signal: AbortSignal,
) => Promise<PwaLineReadingSlot[]>;

type PendingLoad = {
  controller: AbortController;
  promise: Promise<void>;
  settled: boolean;
  waiters: number;
};

function abortError(): DOMException {
  return new DOMException('Aborted', 'AbortError');
}

export class LineReadingResolver {
  private readonly cache = new Map<string, PwaLineReadingSlot>();
  private readonly pending = new Map<string, PendingLoad>();
  readonly lexiconIdentity: string;
  private readonly loader: LineLoader;
  private readonly maxEntries: number;

  constructor(
    lexiconIdentity: string,
    loader: LineLoader,
    maxEntries = 1024,
  ) {
    this.lexiconIdentity = lexiconIdentity;
    this.loader = loader;
    this.maxEntries = maxEntries;
  }

  private cached(literal: string): PwaLineReadingSlot | undefined {
    const value = this.cache.get(literal);
    if (!value) return undefined;
    this.cache.delete(literal);
    this.cache.set(literal, value);
    return value;
  }

  private store(literal: string, slot: PwaLineReadingSlot): void {
    this.cache.delete(literal);
    this.cache.set(literal, slot);
    while (this.cache.size > this.maxEntries) {
      const oldest = this.cache.keys().next().value;
      if (oldest == null) break;
      this.cache.delete(oldest);
    }
  }

  private start(missing: string[], key: string): PendingLoad {
    const controller = new AbortController();
    const entry: PendingLoad = {
      controller,
      promise: Promise.resolve(),
      settled: false,
      waiters: 0,
    };
    entry.promise = this.loader(missing.join(''), controller.signal)
      .then((slots) => {
        const bySurface = new Map(slots.map((slot) => [slot.surface, slot]));
        for (const literal of missing) {
          this.store(literal, bySurface.get(literal) ?? {
            surface: literal,
            kind: 'unresolved',
            choices: [],
            needsChoice: false,
          });
        }
      })
      .finally(() => {
        entry.settled = true;
        if (this.pending.get(key) === entry) this.pending.delete(key);
      });
    this.pending.set(key, entry);
    return entry;
  }

  private wait(entry: PendingLoad, signal?: AbortSignal): Promise<void> {
    if (signal?.aborted) return Promise.reject(abortError());
    entry.waiters += 1;
    return new Promise((resolve, reject) => {
      let finished = false;
      const finish = () => {
        if (finished) return false;
        finished = true;
        signal?.removeEventListener('abort', onAbort);
        entry.waiters -= 1;
        return true;
      };
      const onAbort = () => {
        if (!finish()) return;
        if (!entry.settled && entry.waiters === 0) entry.controller.abort();
        reject(abortError());
      };
      signal?.addEventListener('abort', onAbort, { once: true });
      entry.promise.then(
        () => {
          if (!finish()) return;
          resolve();
        },
        (error) => {
          if (!finish()) return;
          reject(error);
        },
      );
    });
  }

  async resolve(surface: string, signal?: AbortSignal): Promise<PwaLineReadingSlot[]> {
    if (signal?.aborted) throw abortError();
    const literals = Array.from(surface);
    const missing = [...new Set(literals.filter((literal) => !this.cached(literal)))];
    if (missing.length) {
      const key = `${this.lexiconIdentity}\0${missing.join('\0')}`;
      const existing = this.pending.get(key);
      const entry = existing && !existing.controller.signal.aborted
        ? existing
        : this.start(missing, key);
      await this.wait(entry, signal);
    }
    return literals.map((literal) => this.cached(literal) ?? {
      surface: literal,
      kind: 'unresolved',
      choices: [],
      needsChoice: false,
    });
  }
}

export function createLineReadingResolver(
  lexiconIdentity: string,
  loader: LineLoader,
  maxEntries = 1024,
): LineReadingResolver {
  return new LineReadingResolver(lexiconIdentity, loader, maxEntries);
}
