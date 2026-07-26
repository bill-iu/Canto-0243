import type { Last0243SearchMode, PingzeSubMode, UiMode } from '../mode-meta.ts';

export type QueryWorkspaceCommittedFrame = {
  query: string;
  mode: UiMode;
  pzmode: PingzeSubMode;
  fallback0243Mode?: Last0243SearchMode;
};

export interface QueryWorkspaceNavigationAdapter {
  commit(frame: QueryWorkspaceCommittedFrame): void;
}

export function createCallbackNavigationAdapter(
  commitFrame: (frame: QueryWorkspaceCommittedFrame) => void,
): QueryWorkspaceNavigationAdapter {
  return { commit: commitFrame };
}

export function createMemoryNavigationAdapter(): {
  adapter: QueryWorkspaceNavigationAdapter;
  frames: QueryWorkspaceCommittedFrame[];
} {
  const frames: QueryWorkspaceCommittedFrame[] = [];
  return {
    frames,
    adapter: {
      commit(frame) {
        frames.push({ ...frame });
      },
    },
  };
}
