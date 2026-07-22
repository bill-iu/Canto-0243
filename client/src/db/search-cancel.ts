/** Cooperative search cancel — C1 generation discard + C2 hot-path checks. */

export class SearchCancelledError extends Error {
  constructor(message = 'Search cancelled') {
    super(message);
    this.name = 'SearchCancelledError';
  }
}

export type ShouldCancel = () => boolean;

export function throwIfSearchCancelled(shouldCancel?: ShouldCancel): void {
  if (shouldCancel?.()) {
    throw new SearchCancelledError();
  }
}

export function isSearchCancelledError(err: unknown): boolean {
  return err instanceof SearchCancelledError || (err instanceof Error && err.name === 'SearchCancelledError');
}

/** Yield a browser main-thread slice; workers stay throughput-first. */
export async function yieldToMainThread(): Promise<void> {
  if (typeof window === 'undefined') return;
  const scheduler = (globalThis as typeof globalThis & {
    scheduler?: { yield?: () => Promise<void> };
  }).scheduler;
  if (scheduler?.yield) {
    await scheduler.yield();
    return;
  }
  await new Promise<void>((resolve) => setTimeout(resolve, 0));
}
