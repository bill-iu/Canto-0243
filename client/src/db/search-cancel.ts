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
