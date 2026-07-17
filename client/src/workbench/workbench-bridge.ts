import type { WorkbenchStorage } from './line-draft-storage.ts';
import { loadLineDraft } from './line-draft-storage.ts';

export const WORKBENCH_INGEST_KEY = 'canto-workbench-ingest-v1';
export const WORKBENCH_OPEN_SEARCH_KEY = 'canto-workbench-open-search-v1';

export type IngestMode = 'replace' | 'insert';

export interface WorkbenchIngestPayload {
  version: 1;
  literal: string;
  mode: IngestMode;
  createdAt: number;
}

export interface WorkbenchOpenSearchPayload {
  version: 1;
  literal: string;
  createdAt: number;
}

export class WorkbenchBridgeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WorkbenchBridgeError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertLiteral(value: unknown): string {
  if (typeof value !== 'string') throw new WorkbenchBridgeError('literal must be a string');
  const literal = value.trim();
  if (!literal) throw new WorkbenchBridgeError('literal must be non-empty');
  return literal;
}

function clearKey(storage: WorkbenchStorage, key: string): void {
  const removable = storage as WorkbenchStorage & { removeItem?: (k: string) => void };
  if (typeof removable.removeItem === 'function') {
    removable.removeItem(key);
    return;
  }
  storage.setItem(key, '');
}

export function writeIngest(storage: WorkbenchStorage, input: { literal: string; mode: IngestMode }): void {
  const payload: WorkbenchIngestPayload = {
    version: 1,
    literal: assertLiteral(input.literal),
    mode: input.mode === 'insert' ? 'insert' : 'replace',
    createdAt: Date.now(),
  };
  try {
    storage.setItem(WORKBENCH_INGEST_KEY, JSON.stringify(payload));
  } catch {
    throw new WorkbenchBridgeError('sessionStorage unavailable for ingest');
  }
}

export function consumeIngest(storage: WorkbenchStorage): WorkbenchIngestPayload | null {
  const raw = storage.getItem(WORKBENCH_INGEST_KEY);
  try { clearKey(storage, WORKBENCH_INGEST_KEY); } catch { /* still parse below */ }
  if (raw == null || raw === '') return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || value.version !== 1) return null;
    if (value.mode !== 'replace' && value.mode !== 'insert') return null;
    if (!Number.isFinite(value.createdAt)) return null;
    return {
      version: 1,
      literal: assertLiteral(value.literal),
      mode: value.mode,
      createdAt: Number(value.createdAt),
    };
  } catch {
    return null;
  }
}

export function writeOpenSearch(storage: WorkbenchStorage, input: { literal: string }): void {
  const payload: WorkbenchOpenSearchPayload = {
    version: 1,
    literal: assertLiteral(input.literal),
    createdAt: Date.now(),
  };
  try {
    storage.setItem(WORKBENCH_OPEN_SEARCH_KEY, JSON.stringify(payload));
  } catch {
    throw new WorkbenchBridgeError('sessionStorage unavailable for open-search');
  }
}

export function consumeOpenSearch(storage: WorkbenchStorage): WorkbenchOpenSearchPayload | null {
  const raw = storage.getItem(WORKBENCH_OPEN_SEARCH_KEY);
  try { clearKey(storage, WORKBENCH_OPEN_SEARCH_KEY); } catch { /* still parse below */ }
  if (raw == null || raw === '') return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || value.version !== 1) return null;
    if (!Number.isFinite(value.createdAt)) return null;
    return {
      version: 1,
      literal: assertLiteral(value.literal),
      createdAt: Number(value.createdAt),
    };
  } catch {
    return null;
  }
}

/** True when a recoverable non-empty line draft exists. */
export function hasWorkbenchDraft(storage: WorkbenchStorage): boolean {
  const draft = loadLineDraft(storage);
  return Boolean(draft && draft.slots.length > 0 && draft.slots.some((slot) => slot.surface || slot.code));
}

export function readWorkbenchSelectionWidth(storage: WorkbenchStorage): number | null {
  const draft = loadLineDraft(storage);
  return draft?.selection?.width ?? null;
}

export function readWorkbenchSurfacePreview(storage: WorkbenchStorage): string {
  const draft = loadLineDraft(storage);
  if (!draft) return '';
  return draft.surface || draft.slots.map((slot) => slot.surface || '＿').join('');
}
