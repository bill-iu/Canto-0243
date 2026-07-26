import type { QueryWorkspaceSnapshot } from './state.ts';

/**
 * Build the persisted view snapshot without allowing a previous tab's
 * presentation rows to overwrite the active tab during a tab switch.
 */
export function buildPresentationCheckpoint<TResult>(
  snapshot: QueryWorkspaceSnapshot<TResult> | null,
  presentationTabId: number | null,
  presentationResults: readonly TResult[],
  presentationShuffled: boolean,
): QueryWorkspaceSnapshot<TResult> | null {
  if (!snapshot || snapshot.tabId !== presentationTabId) return null;
  const results = presentationShuffled ? [...presentationResults] : [...snapshot.results];
  return {
    ...snapshot,
    results,
    offset: results.length,
  };
}
