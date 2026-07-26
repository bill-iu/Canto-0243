import type { PosFilterState } from '../pos/filter.ts';

export type QueryWorkspaceStatus =
  | 'idle'
  | 'previewing'
  | 'loading'
  | 'loading-more'
  | 'ready'
  | 'error';

export type QueryWorkspaceFrameKind = 'preview' | 'commit';

export interface QueryWorkspaceFrame {
  id: number;
  query: string;
  mode: string;
  pzmode: string;
  kind: QueryWorkspaceFrameKind;
}

export interface QueryWorkspaceSnapshot<TResult> {
  tabId: number;
  q: string;
  results: readonly TResult[];
  offset: number;
  total: number | null;
  posFilter: PosFilterState;
}

export interface QueryWorkspaceDetailIdentity {
  literal: string;
  jyutping: string | null;
}

export interface QueryWorkspaceState<TResult> {
  tabId: number | null;
  draftQuery: string;
  committedFrame: QueryWorkspaceFrame | null;
  activeFrame: QueryWorkspaceFrame | null;
  nextFrameId: number;
  activeFrameId: number | null;
  activeRequestId: number | null;
  status: QueryWorkspaceStatus;
  results: TResult[];
  total: number | null;
  hint: string | null;
  lastPageSize: number;
  offset: number;
  posFilter: PosFilterState;
  detail: QueryWorkspaceDetailIdentity | null;
  error: string | null;
}

export type QueryWorkspaceEvent<TResult> =
  | { type: 'activateTab'; snapshot: QueryWorkspaceSnapshot<TResult> }
  | { type: 'clearQuery'; query: string }
  | {
      type: 'beginFrame';
      query: string;
      mode: string;
      pzmode: string;
      kind: QueryWorkspaceFrameKind;
    }
  | { type: 'requestStarted'; frameId: number; requestId: number; append: boolean }
  | {
      type: 'requestResolved';
      frameId: number;
      requestId: number;
      items: readonly TResult[];
      total: number | null;
      hint?: string | null;
      append: boolean;
    }
  | {
      type: 'requestRejected';
      frameId: number;
      requestId: number;
      message: string;
    }
  | { type: 'setFilter'; posFilter: PosFilterState }
  | { type: 'openDetail'; literal: string; jyutping?: string | null }
  | { type: 'closeDetail' }
  | { type: 'leave' };

function emptyPosFilter(): PosFilterState {
  return { pos: [], family: [], voice: [] };
}

function copyPosFilter(value: PosFilterState): PosFilterState {
  return {
    pos: [...value.pos],
    family: [...value.family],
    voice: [...value.voice],
  };
}

function copyResults<TResult>(items: readonly TResult[]): TResult[] {
  return [...items];
}

export function createInitialQueryWorkspaceState<TResult>(): QueryWorkspaceState<TResult> {
  return {
    tabId: null,
    draftQuery: '',
    committedFrame: null,
    activeFrame: null,
    nextFrameId: 0,
    activeFrameId: null,
    activeRequestId: null,
    status: 'idle',
    results: [],
    total: null,
    hint: null,
    lastPageSize: 0,
    offset: 0,
    posFilter: emptyPosFilter(),
    detail: null,
    error: null,
  };
}

function isCurrentRequest<TResult>(
  state: QueryWorkspaceState<TResult>,
  frameId: number,
  requestId: number,
): boolean {
  return state.activeFrameId === frameId && state.activeRequestId === requestId;
}

export function reduceQueryWorkspace<TResult>(
  state: QueryWorkspaceState<TResult>,
  event: QueryWorkspaceEvent<TResult>,
): QueryWorkspaceState<TResult> {
  switch (event.type) {
    case 'activateTab':
      return {
        ...state,
        tabId: event.snapshot.tabId,
        draftQuery: event.snapshot.q,
        committedFrame: null,
        activeFrame: null,
        activeFrameId: null,
        activeRequestId: null,
        status: event.snapshot.results.length > 0 ? 'ready' : 'idle',
        results: copyResults(event.snapshot.results),
        total: event.snapshot.total,
        hint: null,
        lastPageSize: event.snapshot.results.length,
        offset: event.snapshot.offset,
        posFilter: copyPosFilter(event.snapshot.posFilter),
        detail: null,
        error: null,
      };

    case 'clearQuery':
      return {
        ...state,
        draftQuery: event.query,
        activeFrame: null,
        activeFrameId: null,
        activeRequestId: null,
        status: 'idle',
        results: [],
        total: null,
        hint: null,
        lastPageSize: 0,
        offset: 0,
        detail: null,
        error: null,
      };

    case 'beginFrame': {
      const frameId = state.nextFrameId + 1;
      const frame: QueryWorkspaceFrame = {
        id: frameId,
        query: event.query,
        mode: event.mode,
        pzmode: event.pzmode,
        kind: event.kind,
      };
      return {
        ...state,
        draftQuery: event.query,
        committedFrame: event.kind === 'commit' ? frame : state.committedFrame,
        activeFrame: frame,
        nextFrameId: frameId,
        activeFrameId: frameId,
        activeRequestId: null,
        status: event.kind === 'commit' ? 'loading' : 'previewing',
        error: null,
      };
    }

    case 'requestStarted':
      if (state.activeFrameId !== event.frameId) return state;
      return {
        ...state,
        activeRequestId: event.requestId,
        status: event.append ? 'loading-more' : 'loading',
        error: null,
      };

    case 'requestResolved':
      if (!isCurrentRequest(state, event.frameId, event.requestId)) return state;
      return {
        ...state,
        activeRequestId: null,
        status: 'ready',
        results: event.append ? [...state.results, ...event.items] : copyResults(event.items),
        total: event.total,
        hint: event.hint ?? null,
        lastPageSize: event.items.length,
        offset: event.append ? state.offset + event.items.length : event.items.length,
        error: null,
      };

    case 'requestRejected':
      if (!isCurrentRequest(state, event.frameId, event.requestId)) return state;
      return {
        ...state,
        activeRequestId: null,
        status: 'error',
        error: event.message,
      };

    case 'setFilter':
      return { ...state, posFilter: copyPosFilter(event.posFilter) };

    case 'openDetail':
      return {
        ...state,
        detail: { literal: event.literal, jyutping: event.jyutping ?? null },
      };

    case 'closeDetail':
      return { ...state, detail: null };

    case 'leave':
      return createInitialQueryWorkspaceState<TResult>();

    default:
      return state;
  }
}

export function snapshotFromQueryWorkspace<TResult>(
  state: QueryWorkspaceState<TResult>,
): QueryWorkspaceSnapshot<TResult> | null {
  if (state.tabId == null) return null;
  return {
    tabId: state.tabId,
    q: state.draftQuery,
    results: copyResults(state.results),
    offset: state.offset,
    total: state.total,
    posFilter: copyPosFilter(state.posFilter),
  };
}
