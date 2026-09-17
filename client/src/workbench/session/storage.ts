import { WORKBENCH_DRAFT_KEY, loadLineDraft, validLineDraft, type WorkbenchStorage } from '../line-draft-storage.ts';
import { defaultConstraintsUI, emptySession, sessionFromDraft } from './defaults.ts';
import { normalizeSession, validSession } from './codec.ts';
import { decodeWorkbenchDocument, encodeWorkbenchDocument } from './document.ts';
import type { WorkbenchSession } from './types.ts';

// Stable key; the payload carries its own schema version.
export const WORKBENCH_SESSION_KEY = 'canto-workbench-session-v1';
export const WORKBENCH_SESSION_RECOVERY_KEY = 'canto-workbench-session-recovery-v1';

function decode(raw: string): WorkbenchSession {
  const payload: unknown = JSON.parse(raw);
  if (payload && typeof payload === 'object' && 'version' in payload
    && payload.version === 1 && 'session' in payload && validSession(payload.session)) {
    return normalizeSession(payload.session);
  }
  if (payload && typeof payload === 'object' && 'version' in payload
    && payload.version === 1 && 'draft' in payload && validLineDraft(payload.draft)) {
    return normalizeSession(sessionFromDraft(payload.draft, defaultConstraintsUI()));
  }
  return decodeWorkbenchDocument(payload);
}

function protectExisting(storage: WorkbenchStorage): void {
  const raw = storage.getItem(WORKBENCH_SESSION_KEY);
  if (raw) decode(raw); // Never overwrite a corrupt or newer-version document on mount.
}

/** Validated, portable backup. Does not contain database/cache or panel state. */
export function exportWorkbenchSession(session: WorkbenchSession): string {
  return JSON.stringify(encodeWorkbenchDocument(session));
}

/** Validate before touching storage; quota failures leave the old value intact. */
export function importWorkbenchSession(storage: WorkbenchStorage, raw: string): WorkbenchSession {
  const session = decode(raw);
  const encoded = exportWorkbenchSession(session);
  const previous = storage.getItem(WORKBENCH_SESSION_KEY);
  // Explicit restore may replace unreadable content, but must retain it first.
  if (previous) storage.setItem(WORKBENCH_SESSION_RECOVERY_KEY, previous);
  storage.setItem(WORKBENCH_SESSION_KEY, encoded);
  return session;
}

export function saveWorkbenchSession(storage: WorkbenchStorage, session: WorkbenchSession): void {
  const raw = exportWorkbenchSession(session);
  protectExisting(storage);
  storage.setItem(WORKBENCH_SESSION_KEY, raw);
}

export function clearWorkbenchSession(storage: WorkbenchStorage): void {
  protectExisting(storage);
  const removable = storage as WorkbenchStorage & { removeItem?: (key: string) => void };
  // Clear legacy first: a failed clear must not resurrect a stale draft.
  for (const key of [WORKBENCH_DRAFT_KEY, WORKBENCH_SESSION_KEY]) {
    if (removable.removeItem) removable.removeItem(key);
    else storage.setItem(key, '');
  }
}

/** Read v2, migrate session v1 or draft v1 in memory; write only on a successful save. */
export function loadWorkbenchSession(storage: WorkbenchStorage): WorkbenchSession | null {
  const raw = storage.getItem(WORKBENCH_SESSION_KEY);
  if (raw) {
    try {
      return decode(raw);
    } catch {
      try {
        storage.setItem(WORKBENCH_SESSION_RECOVERY_KEY, raw);
      } catch { /* Original remains untouched even when recovery storage is full. */ }
    }
  }
  const legacy = loadLineDraft(storage);
  return legacy ? normalizeSession(sessionFromDraft(legacy, defaultConstraintsUI())) : null;
}

export function initialSession(storage?: WorkbenchStorage): WorkbenchSession {
  try {
    const store = storage ?? (typeof localStorage !== 'undefined' ? localStorage : null);
    return store ? loadWorkbenchSession(store) ?? emptySession() : emptySession();
  } catch {
    return emptySession();
  }
}
