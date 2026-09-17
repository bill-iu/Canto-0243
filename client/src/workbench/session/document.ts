import type { LineDraft, LineSlot } from '../line-draft.ts';
import { normalizeSession, validSession } from './codec.ts';
import type { WorkbenchSession } from './types.ts';

/** Durable content is independent of the editor's selection and replacement controls. */
export interface WorkbenchContent {
  surface: string;
  slots: Array<Omit<LineSlot, 'locked'>>;
}

type EditorDraft = Omit<LineDraft, 'surface' | 'slots'> & { locks: boolean[] };

/** ponytail: one current line until multi-song editing is a product requirement. */
export interface WorkbenchDocument {
  version: 2;
  content: WorkbenchContent | null;
  editor: Omit<WorkbenchSession, 'draft'> & { draft: EditorDraft | null };
}

export function encodeWorkbenchDocument(session: WorkbenchSession): WorkbenchDocument {
  if (!validSession(session)) throw new Error('Invalid workbench session');
  const { draft, ...editor } = session;
  if (!draft) return { version: 2, content: null, editor: { ...editor, draft: null } };
  const { surface, slots, ...draftState } = draft;
  return {
    version: 2,
    content: { surface, slots: slots.map(({ locked: _locked, ...slot }) => slot) },
    editor: { ...editor, draft: { ...draftState, locks: slots.map((slot) => slot.locked) } },
  };
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function decodeWorkbenchDocument(value: unknown): WorkbenchSession {
  if (!record(value) || value.version !== 2 || !record(value.editor)) {
    throw new Error('Unsupported workbench document');
  }
  const { content, editor } = value;
  let draft: unknown = null;
  if (content !== null || editor.draft !== null) {
    if (!record(content) || !Array.isArray(content.slots) || !record(editor.draft)
      || !Array.isArray(editor.draft.locks) || editor.draft.locks.length !== content.slots.length
      || !editor.draft.locks.every((lock) => typeof lock === 'boolean')) {
      throw new Error('Invalid workbench content');
    }
    const { locks, ...state } = editor.draft;
    draft = {
      ...state,
      surface: content.surface,
      slots: content.slots.map((slot, index) => {
        if (!record(slot)) throw new Error('Invalid workbench slot');
        return { ...slot, locked: locks[index] };
      }),
    };
  }
  const session = { ...editor, draft };
  if (!validSession(session)) throw new Error('Invalid workbench editor state');
  return normalizeSession(session);
}
