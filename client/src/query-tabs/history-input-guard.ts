/** Ignore search-box edits while the browser restores a history entry's form value. */
let blockedUntil = 0;

export function blockSearchInputForHistoryRestore(ms = 300): void {
  blockedUntil = Date.now() + ms;
}

export function isSearchInputBlockedByHistoryRestore(): boolean {
  return Date.now() < blockedUntil;
}
