import type { LineDraft } from '../line-draft.ts';
import { validLineDraft } from '../line-draft-storage.ts';
import { defaultConstraintsUI } from './defaults.ts';
import { syncPhonemeFromConstraints } from './phoneme.ts';
import type { ConstraintsUI, SessionSnapshot, WorkbenchSession } from './types.ts';

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
  if (value.draft !== null && !validLineDraft(value.draft)) return false;
  return validConstraints(value.constraints);
}

export function validSession(value: unknown): value is WorkbenchSession {
  return isRecord(value)
    && Number.isInteger(value.version)
    && Number(value.version) >= 0
    && (value.undo === null || validSnapshot(value.undo))
    && validSnapshot(value);
}

export function normalizeSession(session: WorkbenchSession): WorkbenchSession {
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
