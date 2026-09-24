import type { PosFilterState } from '../pos/filter.ts';
import type { WorkbenchCandidate } from './contracts.ts';
import type { PwaLineReadingChoice, PwaLineReadingSlot } from './pwa-line-readings.ts';
import { sessionReducer } from './session/reducer.ts';
import type { SessionAction, WorkbenchSession } from './session/types.ts';

export type WorkbenchNoticeCode =
  | 'invalid_span'
  | 'reading_failed'
  | 'storage_failed'
  | 'stale_candidate'
  | 'operation_failed';

export interface WorkbenchNotice {
  code: WorkbenchNoticeCode;
  payload?: Record<string, string | number>;
}

export interface WorkbenchActiveRelaxation {
  id: string;
  kind: import('./contracts.ts').RelaxationKind;
  from?: string;
  to?: string;
}

export interface WorkbenchCoordinatorState {
  session: WorkbenchSession;
  readings: PwaLineReadingSlot[];
  preview: WorkbenchCandidate | null;
  activeRelaxation: WorkbenchActiveRelaxation | null;
  posFilter: PosFilterState;
  notice: WorkbenchNotice | null;
  spanInputError: string;
}

export type WorkbenchCoordinatorAction =
  | { type: 'session'; action: SessionAction }
  | { type: 'reading_resolved'; version: number; readings: PwaLineReadingSlot[]; autoChoices: Array<{ pos: number; choice: PwaLineReadingChoice }> }
  | { type: 'reading_failed'; version: number }
  | { type: 'clear_readings' }
  | { type: 'set_preview'; version: number; preview: WorkbenchCandidate | null }
  | { type: 'set_relaxation'; version: number; relaxation: WorkbenchActiveRelaxation | null }
  | { type: 'set_pos_filter'; posFilter: PosFilterState }
  | { type: 'set_notice'; notice: WorkbenchNotice | null }
  | { type: 'set_span_error'; message: string };

export function createWorkbenchCoordinatorState(
  session: WorkbenchSession,
  posFilter: PosFilterState,
): WorkbenchCoordinatorState {
  return {
    session,
    readings: [],
    preview: null,
    activeRelaxation: null,
    posFilter,
    notice: null,
    spanInputError: '',
  };
}

const SURFACE_CHANGING_ACTIONS = new Set<SessionAction['type']>([
  'create_from_parsed',
  'replace_surface',
  'insert_literal',
  'set_slot_manual',
  'apply_span_input',
  'apply_candidate',
  'apply_relaxation',
  'clear',
  'undo',
]);

const WORKFLOW_RESETTING_ACTIONS = new Set<SessionAction['type']>([
  ...SURFACE_CHANGING_ACTIONS,
  'toggle_lock',
  'clear_locks',
  'set_mode',
  'set_semantic',
  'set_code_constraint',
  'set_explicit_code',
  'set_rhyme_picks',
  'set_initial_picks',
  'set_rhyme_ref',
  'set_initial_ref',
]);

function clearWorkflow(state: WorkbenchCoordinatorState): WorkbenchCoordinatorState {
  return {
    ...state,
    preview: null,
    activeRelaxation: null,
    notice: null,
    spanInputError: '',
  };
}

export function workbenchCoordinatorReducer(
  state: WorkbenchCoordinatorState,
  action: WorkbenchCoordinatorAction,
): WorkbenchCoordinatorState {
  switch (action.type) {
    case 'session': {
      const session = sessionReducer(state.session, action.action);
      if (session === state.session) {
        // Stale selection apply: no session change, structured notice only.
        const intent = action.action;
        if (
          (intent.type === 'apply_candidate'
            || intent.type === 'apply_relaxation'
            || intent.type === 'apply_span_input')
          && intent.selectionVersion !== state.session.version
        ) {
          return { ...state, notice: { code: 'stale_candidate' } };
        }
        return state;
      }
      const reset = WORKFLOW_RESETTING_ACTIONS.has(action.action.type)
        ? clearWorkflow(state)
        : state;
      return {
        ...reset,
        session,
        readings: SURFACE_CHANGING_ACTIONS.has(action.action.type) ? [] : reset.readings,
      };
    }
    case 'reading_resolved': {
      if (state.session.version !== action.version) return state;
      let session = state.session;
      for (const { pos, choice } of action.autoChoices) {
        if (session.draft?.slots[pos]?.reading) continue;
        session = sessionReducer(session, {
          type: 'choose_reading',
          pos,
          jyutping: choice.jyutping,
          code: choice.code,
        });
      }
      return { ...state, session, readings: action.readings, notice: null };
    }
    case 'reading_failed':
      return state.session.version === action.version
        ? { ...state, notice: { code: 'reading_failed' } }
        : state;
    case 'clear_readings':
      return state.readings.length ? { ...state, readings: [] } : state;
    case 'set_preview':
      return state.session.version === action.version
        ? { ...state, preview: action.preview }
        : state;
    case 'set_relaxation':
      return state.session.version === action.version
        ? { ...state, activeRelaxation: action.relaxation }
        : state;
    case 'set_pos_filter':
      return { ...state, posFilter: action.posFilter };
    case 'set_notice':
      return { ...state, notice: action.notice };
    case 'set_span_error':
      return { ...state, spanInputError: action.message };
    default:
      return state;
  }
}
