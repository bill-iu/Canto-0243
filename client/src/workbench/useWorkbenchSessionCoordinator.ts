import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';

import type { PosFilterState } from '../pos/filter.ts';
import type { WorkbenchCandidate } from './contracts.ts';
import { LineReadingCoordinator } from './line-reading-coordinator.ts';
import type { LineSlot } from './line-draft.ts';
import {
  createWorkbenchCoordinatorState,
  workbenchCoordinatorReducer,
  type WorkbenchActiveRelaxation,
  type WorkbenchCoordinatorAction,
  type WorkbenchCoordinatorState,
} from './workbench-coordinator.ts';
import {
  clearWorkbenchSession,
  initialSession,
  saveWorkbenchSession,
} from './session/storage.ts';
import type { SessionAction } from './session/types.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';

interface PendingReading {
  surface: string;
  version: number;
  slots: LineSlot[];
}

export interface UseWorkbenchSessionCoordinatorOptions {
  adapter: WorkbenchAdapter;
  active: boolean;
  isReady: boolean;
  initialize: () => Promise<unknown>;
  initialPosFilter: PosFilterState;
}

export interface WorkbenchSessionCoordinator extends WorkbenchCoordinatorState {
  dispatch: (action: WorkbenchCoordinatorAction) => void;
  dispatchSession: (action: SessionAction) => void;
  resolveReadings: (surface: string, version: number, slots: LineSlot[]) => Promise<void>;
  setPreview: (preview: WorkbenchCandidate | null) => void;
  setActiveRelaxation: (relaxation: WorkbenchActiveRelaxation | null, version?: number) => void;
  setPosFilter: (posFilter: PosFilterState) => void;
  setNotice: (notice: WorkbenchCoordinatorState['notice']) => void;
  setSpanInputError: (message: string) => void;
  clearReadings: () => void;
}

export function useWorkbenchSessionCoordinator({
  adapter,
  active,
  isReady,
  initialize,
  initialPosFilter,
}: UseWorkbenchSessionCoordinatorOptions): WorkbenchSessionCoordinator {
  const readingCoordinator = useMemo(() => new LineReadingCoordinator(adapter), [adapter]);
  const [state, dispatch] = useReducer(
    workbenchCoordinatorReducer,
    undefined,
    () => createWorkbenchCoordinatorState(initialSession(), initialPosFilter),
  );
  const stateRef = useRef(state);
  const pendingReadingRef = useRef<PendingReading | null>(null);
  stateRef.current = state;

  useEffect(() => () => readingCoordinator.cancel(), [readingCoordinator]);

  useEffect(() => {
    try {
      if (state.session.draft) saveWorkbenchSession(localStorage, state.session);
      else clearWorkbenchSession(localStorage);
    } catch {
      dispatch({ type: 'set_notice', notice: { code: 'storage_failed' } });
    }
  }, [state.session]);

  const dispatchSession = useCallback((action: SessionAction) => {
    dispatch({ type: 'session', action });
  }, []);

  const resolveReadings = useCallback(async (surface: string, version: number, slots: LineSlot[]) => {
    if (!surface) return;
    const pending = { surface, version, slots };
    pendingReadingRef.current = pending;
    try {
      if (!isReady) await initialize();
      const result = await readingCoordinator.resolve(version, slots, stateRef.current.readings);
      if (pendingReadingRef.current !== pending) return;
      pendingReadingRef.current = null;
      dispatch({ type: 'reading_resolved', ...result });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      if (pendingReadingRef.current === pending) {
        pendingReadingRef.current = null;
        dispatch({ type: 'reading_failed', version });
      }
    }
  }, [initialize, isReady, readingCoordinator]);

  useEffect(() => {
    const pending = pendingReadingRef.current;
    const current = stateRef.current;
    if (!active || !isReady || !pending || current.session.version !== pending.version) return;
    void resolveReadings(pending.surface, pending.version, pending.slots);
  }, [active, isReady, resolveReadings]);

  const setPreview = useCallback((preview: WorkbenchCandidate | null) => {
    dispatch({ type: 'set_preview', version: stateRef.current.session.version, preview });
  }, []);

  const setActiveRelaxation = useCallback((relaxation: WorkbenchActiveRelaxation | null, version = stateRef.current.session.version) => {
    dispatch({ type: 'set_relaxation', version, relaxation });
  }, []);

  const setPosFilter = useCallback((posFilter: PosFilterState) => {
    dispatch({ type: 'set_pos_filter', posFilter });
  }, []);

  const setNotice = useCallback((notice: WorkbenchCoordinatorState['notice']) => {
    dispatch({ type: 'set_notice', notice });
  }, []);

  const setSpanInputError = useCallback((message: string) => {
    dispatch({ type: 'set_span_error', message });
  }, []);

  const clearReadings = useCallback(() => {
    dispatch({ type: 'clear_readings' });
  }, []);

  return {
    ...state,
    dispatch,
    dispatchSession,
    resolveReadings,
    setPreview,
    setActiveRelaxation,
    setPosFilter,
    setNotice,
    setSpanInputError,
    clearReadings,
  };
}
