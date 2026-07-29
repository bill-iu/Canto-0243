import type { LineDraft } from '../line-draft.ts';
import {
  WORKBENCH_DRAFT_KEY,
  loadLineDraft,
  saveLineDraft,
  type WorkbenchStorage,
} from '../line-draft-storage.ts';
import { defaultConstraintsUI, emptySession, sessionFromDraft } from './defaults.ts';
import { syncPhonemeFromConstraints } from './phoneme.ts';
import type { ConstraintsUI, SessionSnapshot, WorkbenchSession } from './types.ts';

export const WORKBENCH_SESSION_KEY = 'canto-workbench-session-v1';
export const WORKBENCH_SESSION_RECOVERY_KEY = 'canto-workbench-session-recovery-v1';

const MAX_RECOVERY_LENGTH = 16_384;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function validPicks(value: unknown): boolean {
  return isRecord(value)
    && typeof value.whole === 'boolean'
    && typeof value.head === 'boolean'
    && typeof value.tail === 'boolean'
    && Array.isArray(value.middles)
    && value.middles.every((m) => Number.isInteger(m));
}

function validConstraints(value: unknown): value is ConstraintsUI {
  if (!isRecord(value)) return false;
  if (value.mode !== 'm1' && value.mode !== 'm2' && value.mode !== 'm3') return false;
  if (value.semanticIntent !== 'ranked' && value.semanticIntent !== 'direct_only' && value.semanticIntent !== 'off') {
    return false;
  }
  if (value.codeConstraint !== 'same_tone' && value.codeConstraint !== 'off' && value.codeConstraint !== 'explicit') {
    return false;
  }
  if (typeof value.explicitCode !== 'string') return false;
  // rhymeProfile optional for older snapshots (default exact)
  if (
    value.rhymeProfile != null
    && value.rhymeProfile !== 'exact'
    && value.rhymeProfile !== 'tong'
    && value.rhymeProfile !== 'nucleus'
    && value.rhymeProfile !== 'coda'
  ) {
    return false;
  }
  if (!validPicks(value.rhymePicks) || !validPicks(value.initialPicks)) return false;
  if (typeof value.rhymeRef !== 'string' || typeof value.initialRef !== 'string') return false;
  if (!isRecord(value.refReadings)) return false;
  return Object.values(value.refReadings).every((v) => typeof v === 'string');
}

function validDraftShape(draft: unknown): draft is LineDraft {
  const store = new Map<string, string>();
  const mem: WorkbenchStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => { store.set(key, value); },
  };
  try {
    saveLineDraft(mem, draft as LineDraft);
    return loadLineDraft(mem) != null;
  } catch {
    return false;
  }
}

function hydrateDraftCodes(draft: LineDraft): LineDraft {
  let changed = false;
  const slots = draft.slots.map((slot, pos) => {
    if (slot.code) return slot;
    const digit = draft.constraints.find((item) => item.kind === 'code_digit' && item.pos === pos)?.digit;
    if (!digit) return slot;
    changed = true;
    return { ...slot, code: digit };
  });
  if (!changed) return draft;
  return { ...draft, slots };
}

function validSnapshot(value: unknown): value is SessionSnapshot {
  if (!isRecord(value)) return false;
  if (value.draft !== null && !validDraftShape(value.draft)) return false;
  return validConstraints(value.constraints);
}

function validSession(value: unknown): value is WorkbenchSession {
  return isRecord(value)
    && Number.isInteger(value.version)
    && Number(value.version) >= 0
    && (value.undo === null || validSnapshot(value.undo))
    && validSnapshot(value);
}

function retainRecovery(storage: WorkbenchStorage, raw: string): void {
  try {
    storage.setItem(WORKBENCH_SESSION_RECOVERY_KEY, raw.slice(0, MAX_RECOVERY_LENGTH));
  } catch {
    // ignore
  }
}

function normalizeSession(session: WorkbenchSession): WorkbenchSession {
  const constraints = {
    ...defaultConstraintsUI(),
    ...session.constraints,
    rhymeProfile: session.constraints.rhymeProfile ?? 'exact',
  };
  let draft = session.draft;
  if (draft) {
    draft = hydrateDraftCodes(draft);
    draft = syncPhonemeFromConstraints(draft, constraints);
    const version = session.version || draft.version;
    draft = { ...draft, version };
    return { ...session, draft, constraints, version };
  }
  return { ...session, constraints, version: session.version || 0 };
}

export function saveWorkbenchSession(storage: WorkbenchStorage, session: WorkbenchSession): void {
  storage.setItem(WORKBENCH_SESSION_KEY, JSON.stringify({ version: 1, session }));
}

export function clearWorkbenchSession(storage: WorkbenchStorage): void {
  const removable = storage as WorkbenchStorage & { removeItem?: (key: string) => void };
  if (typeof removable.removeItem === 'function') {
    removable.removeItem(WORKBENCH_SESSION_KEY);
    removable.removeItem(WORKBENCH_DRAFT_KEY);
    return;
  }
  storage.setItem(WORKBENCH_SESSION_KEY, '');
  storage.setItem(WORKBENCH_DRAFT_KEY, '');
}

/** Load session v1, else migrate draft v1, else null. */
export function loadWorkbenchSession(storage: WorkbenchStorage): WorkbenchSession | null {
  const raw = storage.getItem(WORKBENCH_SESSION_KEY);
  if (raw != null && raw !== '') {
    try {
      const payload: unknown = JSON.parse(raw);
      if (isRecord(payload) && payload.version === 1 && validSession(payload.session)) {
        return normalizeSession(payload.session);
      }
    } catch {
      // retain below
    }
    retainRecovery(storage, raw);
  }

  const legacy = loadLineDraft(storage);
  if (legacy) {
    return normalizeSession(sessionFromDraft(hydrateDraftCodes(legacy), defaultConstraintsUI()));
  }
  return null;
}

export function initialSession(storage?: WorkbenchStorage): WorkbenchSession {
  try {
    const store = storage ?? (typeof localStorage !== 'undefined' ? localStorage : null);
    if (!store) return emptySession();
    return loadWorkbenchSession(store) ?? emptySession();
  } catch {
    return emptySession();
  }
}
