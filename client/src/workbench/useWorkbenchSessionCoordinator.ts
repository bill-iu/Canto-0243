import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';

import type { PosFilterState } from '../pos/filter.ts';
import type { WorkbenchCandidate } from './contracts.ts';
import type { LineSlot } from './line-draft.ts';
import {
  createWorkbenchCoordinatorState,
  workbenchCoordinatorReducer,
  type WorkbenchActiveRelaxation,
  type WorkbenchCoordinatorState,
} from './workbench-coordinator.ts';
import {
  clearWorkbenchSession,
  initialSession,
  saveWorkbenchSession,
} from './session/storage.ts';
import type { SessionAction } from './session/types.ts';
import type { WorkbenchAdapter } from './workbench-adapter.ts';
import {
  missingReferenceChars,
  WorkbenchReadingLifecycle,
} from './workbench-reading-lifecycle.ts';

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

export interface WorkbenchSessionCoordinator {
  model: WorkbenchCoordinatorState;
  actions: {
    createDraft: (draft: Extract<SessionAction, { type: 'create_from_parsed' }>['draft']) => void;
    replaceSurface: (literal: string) => void;
    insertLiteral: (literal: string) => void;
    chooseMode: (mode: Extract<SessionAction, { type: 'set_mode' }>['mode']) => void;
    chooseSemanticIntent: (semanticIntent: Extract<SessionAction, { type: 'set_semantic' }>['semanticIntent']) => void;
    chooseCodeConstraint: (mode: Extract<SessionAction, { type: 'set_code_constraint' }>['mode']) => void;
    changeExplicitCode: (raw: string) => void;
    toggleLock: (pos: number) => void;
    clearLocks: () => void;
    changeRhymePicks: (picks: Extract<SessionAction, { type: 'set_rhyme_picks' }>['picks']) => void;
    changeInitialPicks: (picks: Extract<SessionAction, { type: 'set_initial_picks' }>['picks']) => void;
    changeRhymeRef: (value: string) => void;
    changeInitialRef: (value: string) => void;
    chooseReading: (pos: number, jyutping: string, code: string) => void;
    changeManualSlot: (pos: number, surface: string, code: string) => void;
    clearDraft: () => void;
    applySpanInput: (action: Omit<Extract<SessionAction, { type: 'apply_span_input' }>, 'type'>) => void;
    undo: () => void;
    applyCandidate: (action: Omit<Extract<SessionAction, { type: 'apply_candidate' }>, 'type'>) => void;
    applyRelaxation: (action: Omit<Extract<SessionAction, { type: 'apply_relaxation' }>, 'type'>) => void;
    resolveReadings: (surface: string, version: number, slots: LineSlot[]) => Promise<void>;
    previewCandidate: (preview: WorkbenchCandidate) => void;
    dismissPreview: () => void;
    rememberRelaxation: (relaxation: WorkbenchActiveRelaxation | null, version?: number) => void;
    changePosFilter: (posFilter: PosFilterState) => void;
    reportSpanError: (message: string) => void;
  };
}

export function useWorkbenchSessionCoordinator({
  adapter,
  active,
  isReady,
  initialize,
  initialPosFilter,
}: UseWorkbenchSessionCoordinatorOptions): WorkbenchSessionCoordinator {
  const readingLifecycle = useMemo(() => new WorkbenchReadingLifecycle(adapter), [adapter]);
  const [state, dispatch] = useReducer(
    workbenchCoordinatorReducer,
    undefined,
    () => createWorkbenchCoordinatorState(initialSession(), initialPosFilter),
  );
  const stateRef = useRef(state);
  const activeRef = useRef(active);
  const pendingReadingRef = useRef<PendingReading | null>(null);
  stateRef.current = state;
  activeRef.current = active;

  useEffect(() => () => readingLifecycle.cancel(), [readingLifecycle]);

  useEffect(() => {
    readingLifecycle.setActive(active);
    if (!active) pendingReadingRef.current = null;
  }, [active, readingLifecycle]);

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
      const result = await readingLifecycle.resolveLine(version, slots, stateRef.current.readings);
      if (!activeRef.current || pendingReadingRef.current !== pending) return;
      pendingReadingRef.current = null;
      dispatch({ type: 'reading_resolved', ...result });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      if (pendingReadingRef.current === pending) {
        pendingReadingRef.current = null;
        dispatch({ type: 'reading_failed', version });
      }
    }
  }, [initialize, isReady, readingLifecycle]);

  useEffect(() => {
    const pending = pendingReadingRef.current;
    const current = stateRef.current;
    if (!active || !isReady || !pending || current.session.version !== pending.version) return;
    void resolveReadings(pending.surface, pending.version, pending.slots);
  }, [active, isReady, resolveReadings]);

  useEffect(() => {
    if (!active || !isReady) return;
    const { rhymeRef, initialRef, refReadings } = state.session.constraints;
    const needed = missingReferenceChars([rhymeRef, initialRef], refReadings);
    if (!needed.length) return;
    void readingLifecycle.resolveReferences(needed).then(
      (readings) => {
        if (activeRef.current && Object.keys(readings).length) {
          dispatch({ type: 'session', action: { type: 'merge_ref_readings', readings } });
        }
      },
      (error: unknown) => {
        if (!(error instanceof DOMException) || error.name !== 'AbortError') {
          // Surface fallbacks remain usable while the lexicon is unavailable.
        }
      },
    );
  }, [
    active,
    isReady,
    readingLifecycle,
    state.session.constraints.initialRef,
    state.session.constraints.refReadings,
    state.session.constraints.rhymeRef,
  ]);

  const setPreview = useCallback((preview: WorkbenchCandidate | null) => {
    dispatch({ type: 'set_preview', version: stateRef.current.session.version, preview });
  }, []);

  const setActiveRelaxation = useCallback((relaxation: WorkbenchActiveRelaxation | null, version = stateRef.current.session.version) => {
    dispatch({ type: 'set_relaxation', version, relaxation });
  }, []);

  const setPosFilter = useCallback((posFilter: PosFilterState) => {
    dispatch({ type: 'set_pos_filter', posFilter });
  }, []);

  const setSpanInputError = useCallback((message: string) => {
    dispatch({ type: 'set_span_error', message });
  }, []);

  return {
    model: state,
    actions: {
      createDraft: (draft) => dispatchSession({ type: 'create_from_parsed', draft }),
      replaceSurface: (literal) => dispatchSession({ type: 'replace_surface', literal }),
      insertLiteral: (literal) => dispatchSession({ type: 'insert_literal', literal }),
      chooseMode: (mode) => dispatchSession({ type: 'set_mode', mode }),
      chooseSemanticIntent: (semanticIntent) => dispatchSession({ type: 'set_semantic', semanticIntent }),
      chooseCodeConstraint: (mode) => dispatchSession({ type: 'set_code_constraint', mode }),
      changeExplicitCode: (raw) => dispatchSession({ type: 'set_explicit_code', raw }),
      toggleLock: (pos) => dispatchSession({ type: 'toggle_lock', pos }),
      clearLocks: () => dispatchSession({ type: 'clear_locks' }),
      changeRhymePicks: (picks) => dispatchSession({ type: 'set_rhyme_picks', picks }),
      changeInitialPicks: (picks) => dispatchSession({ type: 'set_initial_picks', picks }),
      changeRhymeRef: (value) => dispatchSession({ type: 'set_rhyme_ref', value }),
      changeInitialRef: (value) => dispatchSession({ type: 'set_initial_ref', value }),
      chooseReading: (pos, jyutping, code) => dispatchSession({ type: 'choose_reading', pos, jyutping, code }),
      changeManualSlot: (pos, surface, code) => dispatchSession({ type: 'set_slot_manual', pos, surface, code }),
      clearDraft: () => dispatchSession({ type: 'clear' }),
      applySpanInput: (action) => dispatchSession({ type: 'apply_span_input', ...action }),
      undo: () => dispatchSession({ type: 'undo' }),
      applyCandidate: (action) => dispatchSession({ type: 'apply_candidate', ...action }),
      applyRelaxation: (action) => dispatchSession({ type: 'apply_relaxation', ...action }),
      resolveReadings,
      previewCandidate: (preview) => setPreview(preview),
      dismissPreview: () => setPreview(null),
      rememberRelaxation: setActiveRelaxation,
      changePosFilter: setPosFilter,
      reportSpanError: setSpanInputError,
    },
  };
}
