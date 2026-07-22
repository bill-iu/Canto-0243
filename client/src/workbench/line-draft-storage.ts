import type { LineDraft } from './line-draft.ts';

export const WORKBENCH_DRAFT_KEY = 'canto-workbench-draft-v1';
export const WORKBENCH_RECOVERY_KEY = 'canto-workbench-draft-recovery-v1';

const MAX_RECOVERY_LENGTH = 16_384;

export interface WorkbenchStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function validSlot(value: unknown): boolean {
  return isRecord(value)
    && typeof value.surface === 'string'
    && Array.from(value.surface).length <= 1
    && typeof value.locked === 'boolean'
    && (value.reading == null || typeof value.reading === 'string')
    && (value.code == null || typeof value.code === 'string');
}

function validSelection(value: unknown, length: number): boolean {
  return value === null || (
    isRecord(value)
    && Number.isInteger(value.start)
    && Number(value.start) >= 0
    && Number.isInteger(value.width)
    && Number(value.width) >= 1
    && Number(value.width) <= 4
    && Number(value.start) + Number(value.width) <= length
  );
}

function validConstraint(value: unknown, length: number): boolean {
  if (!isRecord(value) || !Number.isInteger(value.pos) || Number(value.pos) < 0 || Number(value.pos) >= length) {
    return false;
  }
  if (value.kind === 'code_digit') return typeof value.digit === 'string' && /^\d$/.test(value.digit);
  if (value.kind === 'literal_char') return typeof value.literal === 'string' && Array.from(value.literal).length === 1;
  if (value.kind === 'final_anchor' || value.kind === 'initial_anchor') return typeof value.ref === 'string' && value.ref.length > 0;
  return value.kind === 'tone_class' && (value.toneClass === 'ping' || value.toneClass === 'ze');
}

function validLastApplied(value: unknown): boolean {
  return value === null || (
    isRecord(value)
    && (value.kind === 'candidate' || value.kind === 'relaxation' || value.kind === 'manual')
    && (value.literal == null || typeof value.literal === 'string')
    && (value.relaxationId == null || typeof value.relaxationId === 'string')
  );
}

function validSnapshot(value: unknown): boolean {
  if (!isRecord(value) || typeof value.surface !== 'string' || !Array.isArray(value.slots)) return false;
  const slots = value.slots;
  if (slots.length < 1 || slots.length > 64 || !slots.every(validSlot)) return false;
  if (value.surface !== slots.map((slot) => (slot as { surface: string }).surface).join('')) return false;
  return validSelection(value.selection, slots.length)
    && Array.isArray(value.constraints)
    && value.constraints.every((item) => validConstraint(item, slots.length))
    && validLastApplied(value.lastApplied);
}

function validDraft(value: unknown): value is LineDraft {
  return validSnapshot(value)
    && isRecord(value)
    && Number.isInteger(value.version)
    && Number(value.version) >= 1
    && (value.undo === null || validSnapshot(value.undo));
}

function retainRecovery(storage: WorkbenchStorage, raw: string): void {
  try {
    storage.setItem(WORKBENCH_RECOVERY_KEY, raw.slice(0, MAX_RECOVERY_LENGTH));
  } catch {
    // Storage may be unavailable or full; loading still falls back safely.
  }
}

export function saveLineDraft(storage: WorkbenchStorage, draft: LineDraft): void {
  storage.setItem(WORKBENCH_DRAFT_KEY, JSON.stringify({ version: 1, draft }));
}

export function clearLineDraft(storage: WorkbenchStorage): void {
  const removable = storage as WorkbenchStorage & { removeItem?: (key: string) => void };
  if (typeof removable.removeItem === 'function') {
    removable.removeItem(WORKBENCH_DRAFT_KEY);
    return;
  }
  storage.setItem(WORKBENCH_DRAFT_KEY, '');
}

export function loadLineDraft(storage: WorkbenchStorage): LineDraft | null {
  const raw = storage.getItem(WORKBENCH_DRAFT_KEY);
  if (raw == null || raw === '') return null;

  try {
    const payload: unknown = JSON.parse(raw);
    if (isRecord(payload) && payload.version === 1 && validDraft(payload.draft)) return payload.draft;
  } catch {
    // Retain the original payload below before returning a clean state.
  }

  retainRecovery(storage, raw);
  return null;
}
