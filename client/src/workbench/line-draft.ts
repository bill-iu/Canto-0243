import type { WorkbenchSlotConstraintV1 } from './contracts.ts';
import { parseLineInput, type InputConstraint, type ParsedLineInput } from './line-input.ts';

export interface LineSlot {
  surface: string;
  reading?: string;
  code?: string;
  locked: boolean;
}

export interface LineSelection {
  start: number;
  width: number;
}

export interface LastApplied {
  kind: 'candidate' | 'relaxation' | 'manual';
  literal?: string;
  relaxationId?: string;
}

interface DraftSnapshot {
  surface: string;
  slots: LineSlot[];
  selection: LineSelection | null;
  constraints: WorkbenchSlotConstraintV1[];
  lastApplied: LastApplied | null;
}

export interface LineDraft extends DraftSnapshot {
  version: number;
  undo: DraftSnapshot | null;
}

export type LineDraftAction =
  | { type: 'select'; start: number; width: number }
  | { type: 'toggle_lock'; pos: number }
  | { type: 'lock_selection' }
  | { type: 'choose_reading'; pos: number; jyutping: string; code: string }
  | { type: 'set_constraint'; constraint: WorkbenchSlotConstraintV1 }
  | { type: 'replace_surface'; literal: string }
  | { type: 'insert_literal'; literal: string }
  | { type: 'set_slot_manual'; pos: number; surface: string; code?: string }
  | {
      type: 'apply_span_input';
      selectionVersion: number;
      slots: Array<{ surface: string; reading?: string; code?: string }>;
      constraints: WorkbenchSlotConstraintV1[];
    }
  | {
      type: 'apply_candidate';
      selectionVersion: number;
      literal: string;
      jyutping: string;
      code: string;
      relaxationId?: string;
    }
  | {
      type: 'apply_relaxation';
      selectionVersion: number;
      relaxationId: string;
      constraints: WorkbenchSlotConstraintV1[];
    }
  | { type: 'undo' };

function snapshot(draft: LineDraft): DraftSnapshot {
  return {
    surface: draft.surface,
    slots: draft.slots,
    selection: draft.selection,
    constraints: draft.constraints,
    lastApplied: draft.lastApplied,
  };
}

function withEdit(draft: LineDraft, change: Partial<DraftSnapshot>, undo = draft.undo): LineDraft {
  return { ...draft, ...change, version: draft.version + 1, undo };
}

export function createLineDraft(parsed: Extract<ParsedLineInput, { ok: true }>): LineDraft {
  const slots = parsed.slots.map((slot, pos) => {
    const digit = parsed.constraints.find(
      (item): item is Extract<InputConstraint, { kind: 'code_digit' }> =>
        item.kind === 'code_digit' && item.pos === pos,
    );
    return {
      ...slot,
      locked: false,
      code: slot.code || digit?.digit,
    };
  });
  return {
    version: 1,
    surface: slots.map((slot) => slot.surface).join(''),
    slots,
    selection: null,
    constraints: parsed.constraints,
    lastApplied: null,
    undo: null,
  };
}

function applyCandidate(
  draft: LineDraft,
  action: Extract<LineDraftAction, { type: 'apply_candidate' }>,
): LineDraft {
  const selection = draft.selection;
  if (!selection || action.selectionVersion !== draft.version) return draft;

  const literals = Array.from(action.literal);
  const readings = action.jyutping.trim().split(/\s+/);
  const codes = Array.from(action.code);
  if (literals.length !== selection.width || readings.length !== selection.width || codes.length !== selection.width) {
    return draft;
  }

  const slots = draft.slots.slice();
  for (let offset = 0; offset < selection.width; offset += 1) {
    const pos = selection.start + offset;
    const current = slots[pos];
    if (!current) return draft;
    slots[pos] = {
      ...current,
      surface: literals[offset] ?? '',
      reading: readings[offset],
      code: codes[offset],
    };
  }

  return withEdit(
    draft,
    {
      slots,
      surface: slots.map((slot) => slot.surface).join(''),
      lastApplied: { kind: 'candidate', literal: action.literal, relaxationId: action.relaxationId },
    },
    snapshot(draft),
  );
}

export function lineDraftReducer(draft: LineDraft, action: LineDraftAction): LineDraft {
  switch (action.type) {
    case 'select': {
      if (
        !Number.isInteger(action.start)
        || !Number.isInteger(action.width)
        || action.start < 0
        || action.width < 1
        || action.width > draft.slots.length
        || action.start + action.width > draft.slots.length
      ) return draft;
      if (draft.selection?.start === action.start && draft.selection.width === action.width) return draft;
      return withEdit(draft, { selection: { start: action.start, width: action.width } });
    }
    case 'toggle_lock': {
      const current = draft.slots[action.pos];
      if (!current) return draft;
      // Prefer toggleLockKeepingSpan in UI — kept for keyboard/tests that only flip the flag.
      const slots = draft.slots.slice();
      slots[action.pos] = { ...current, locked: !current.locked };
      return withEdit(draft, { slots });
    }
    case 'lock_selection': {
      // Deprecated: 圈選已廢；保留 no-op 以免舊草稿／捷徑炸。
      return draft;
    }
    case 'choose_reading': {
      const current = draft.slots[action.pos];
      if (!current || !action.jyutping || !action.code) return draft;
      const slots = draft.slots.slice();
      slots[action.pos] = { ...current, reading: action.jyutping, code: action.code };
      return withEdit(draft, { slots });
    }
    case 'set_constraint': {
      if (action.constraint.pos < 0 || action.constraint.pos >= draft.slots.length) return draft;
      const constraints = draft.constraints.filter((item) => !(
        item.pos === action.constraint.pos && item.kind === action.constraint.kind
      ));
      constraints.push(action.constraint);
      return withEdit(draft, { constraints });
    }
    case 'replace_surface': {
      const parsed = parseLineInput(action.literal);
      if (!parsed.ok || parsed.kind !== 'surface') return draft;
      const next = createLineDraft(parsed);
      return {
        ...next,
        version: draft.version + 1,
        undo: snapshot(draft),
      };
    }
    case 'insert_literal': {
      const selection = draft.selection;
      if (!selection) return draft;
      const literals = Array.from(action.literal.trim());
      if (literals.length !== selection.width) return draft;
      const slots = draft.slots.slice();
      for (let offset = 0; offset < selection.width; offset += 1) {
        const pos = selection.start + offset;
        const current = slots[pos];
        if (!current) return draft;
        slots[pos] = {
          ...current,
          surface: literals[offset] ?? '',
          reading: undefined,
          code: undefined,
        };
      }
      return withEdit(
        draft,
        {
          slots,
          surface: slots.map((slot) => slot.surface).join(''),
          lastApplied: null,
        },
        snapshot(draft),
      );
    }
    case 'set_slot_manual': {
      const current = draft.slots[action.pos];
      if (!current) return draft;
      const surface = action.surface ?? '';
      const code = action.code;
      if ((surface && code) || (!surface && !code) || code === '?') return draft;
      if (surface && Array.from(surface).length !== 1) return draft;
      if (code && !/^[0-9]$/.test(code)) return draft;
      const slots = draft.slots.slice();
      if (surface === '?') {
        slots[action.pos] = { ...current, surface: '?', reading: undefined }; // keep code
        const constraints = draft.constraints.filter((item) => !(item.pos === action.pos && item.kind === 'tone_class'));
        return withEdit(draft, {
          slots, surface: slots.map((s) => s.surface).join(''), constraints, lastApplied: { kind: 'manual', literal: '?' },
        }, snapshot(draft));
      }
      slots[action.pos] = { ...current, surface: surface || '', reading: undefined, code: code || undefined };
      const constraints = draft.constraints.filter((item) => !(
        item.pos === action.pos && (item.kind === 'code_digit' || item.kind === 'tone_class')
      ));
      if (code) constraints.push({ pos: action.pos, kind: 'code_digit', digit: code });
      return withEdit(draft, {
        slots, surface: slots.map((s) => s.surface).join(''), constraints, lastApplied: { kind: 'manual', literal: surface || code },
      }, snapshot(draft));
    }
    case 'apply_span_input': {
      const selection = draft.selection;
      if (!selection || action.selectionVersion !== draft.version) return draft;
      if (action.slots.length !== selection.width) return draft;
      const slots = draft.slots.slice();
      for (let i = 0; i < selection.width; i += 1) {
        const pos = selection.start + i;
        const current = slots[pos];
        const incoming = action.slots[i];
        if (!current || !incoming) return draft;
        slots[pos] = { ...current, surface: incoming.surface, reading: incoming.reading, code: incoming.code };
      }
      const { start, width } = selection;
      const kept = draft.constraints.filter((item) => item.pos < start || item.pos >= start + width);
      const remapped = action.constraints.map((item) => ({ ...item, pos: item.pos + start }));
      return withEdit(
        draft,
        {
          slots,
          surface: slots.map((slot) => slot.surface).join(''),
          constraints: [...kept, ...remapped],
          lastApplied: { kind: 'manual', literal: action.slots.map((s) => s.surface || s.code || '').join('') },
        },
        snapshot(draft),
      );
    }
    case 'apply_candidate':
      return applyCandidate(draft, action);
    case 'apply_relaxation':
      if (action.selectionVersion !== draft.version) return draft;
      return withEdit(
        draft,
        {
          constraints: action.constraints,
          lastApplied: { kind: 'relaxation', relaxationId: action.relaxationId },
        },
        snapshot(draft),
      );
    case 'undo':
      if (!draft.undo) return draft;
      return { ...draft.undo, version: draft.version + 1, undo: null };
  }
}
