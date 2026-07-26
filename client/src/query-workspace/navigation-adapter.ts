import type { Last0243SearchMode, PingzeSubMode, UiMode } from '../mode-meta.ts';
import type { QueryResult } from '../db/query.ts';
import type { QueryWorkspaceSnapshot } from './state.ts';

export type QueryWorkspaceCommittedFrame = {
  query: string;
  mode: UiMode;
  pzmode: PingzeSubMode;
  fallback0243Mode?: Last0243SearchMode;
};

export interface QueryWorkspaceNavigationAdapter {
  commit(frame: QueryWorkspaceCommittedFrame): void;
  checkpoint(tabId: number, snapshot: QueryWorkspaceSnapshot<QueryResult>): void;
}

export function createCallbackNavigationAdapter(
  options: {
    commitFrame: (frame: QueryWorkspaceCommittedFrame) => void;
    checkpoint: (tabId: number, snapshot: QueryWorkspaceSnapshot<QueryResult>) => void;
  },
): QueryWorkspaceNavigationAdapter {
  return {
    commit: options.commitFrame,
    checkpoint: options.checkpoint,
  };
}

export function createMemoryNavigationAdapter(): {
  adapter: QueryWorkspaceNavigationAdapter;
  frames: QueryWorkspaceCommittedFrame[];
  checkpoints: Array<{ tabId: number; snapshot: QueryWorkspaceSnapshot<QueryResult> }>;
} {
  const frames: QueryWorkspaceCommittedFrame[] = [];
  const checkpoints: Array<{ tabId: number; snapshot: QueryWorkspaceSnapshot<QueryResult> }> = [];
  return {
    frames,
    checkpoints,
    adapter: {
      commit(frame) {
        frames.push({ ...frame });
      },
      checkpoint(tabId, snapshot) {
        checkpoints.push({
          tabId,
          snapshot: {
            ...snapshot,
            results: [...snapshot.results],
            posFilter: {
              pos: [...snapshot.posFilter.pos],
              family: [...snapshot.posFilter.family],
              voice: [...snapshot.posFilter.voice],
            },
          },
        });
      },
    },
  };
}
