import {
  codeConstraintAfterRemoveCode,
  sameToneCodePattern,
  sanitizeExplicitCode,
} from '../code-constraint.ts';
import { createLineDraft, lineDraftReducer, type LineDraft } from '../line-draft.ts';
import { parseLineInput } from '../line-input.ts';
import { toggleLockKeepingSpan } from '../replacement-span.ts';
import { defaultConstraintsUI } from './defaults.ts';
import { fitConstraintsToSpan, syncPhonemeFromConstraints } from './phoneme.ts';
import type {
  ConstraintsUI,
  SessionAction,
  SessionSnapshot,
  ToggleLockSessionResult,
  WorkbenchSession,
} from './types.ts';

function snap(session: WorkbenchSession): SessionSnapshot {
  return {
    draft: session.draft,
    constraints: session.constraints,
  };
}

function alignVersion(draft: LineDraft | null, version: number): LineDraft | null {
  if (!draft) return null;
  if (draft.version === version) return draft;
  return { ...draft, version };
}

function commit(
  session: WorkbenchSession,
  next: { draft: LineDraft | null; constraints: ConstraintsUI },
  opts: { undo?: boolean; syncPhoneme?: boolean } = {},
): WorkbenchSession {
  const version = session.version + 1;
  let draft = next.draft;
  if (draft) {
    // 預設由 constraintsUI 寫 phoneme 錨；放寬後跟 plan 槽位時可 skip，避免 picks 重注已移除嘅錨
    if (opts.syncPhoneme !== false) {
      draft = syncPhonemeFromConstraints(draft, next.constraints);
    }
    draft = alignVersion(draft, version)!;
  }
  return {
    draft,
    constraints: next.constraints,
    version,
    undo: opts.undo ? snap(session) : session.undo,
  };
}

function withDraftAction(
  session: WorkbenchSession,
  action: Parameters<typeof lineDraftReducer>[1],
  opts: { undo?: boolean } = {},
): WorkbenchSession {
  if (!session.draft) return session;
  // 與 session.version 對齊，令 apply_* 嘅 selectionVersion 檢查一致
  const aligned = alignVersion(session.draft, session.version)!;
  const nextDraft = lineDraftReducer(aligned, action);
  if (nextDraft === aligned) return session;
  const width = nextDraft.selection?.width ?? 0;
  const constraints = fitConstraintsToSpan(
    session.constraints,
    width,
    nextDraft.slots,
    nextDraft.selection,
  );
  return commit(session, { draft: nextDraft, constraints }, { undo: opts.undo });
}

export function sessionReducer(session: WorkbenchSession, action: SessionAction): WorkbenchSession {
  switch (action.type) {
    case 'create_from_parsed': {
      const constraints = defaultConstraintsUI();
      const version = session.version + 1;
      let draft = syncPhonemeFromConstraints(action.draft, constraints);
      draft = alignVersion(draft, version)!;
      // 新建句格唔保留上一份 undo（同舊 page 行為）
      return { draft, constraints, version, undo: null };
    }
    case 'replace_surface': {
      if (!session.draft) {
        const parsed = parseLineInput(action.literal);
        if (!parsed.ok || parsed.kind !== 'surface') return session;
        const constraints = defaultConstraintsUI();
        const version = session.version + 1;
        let draft = syncPhonemeFromConstraints(createLineDraft(parsed), constraints);
        draft = alignVersion(draft, version)!;
        return { draft, constraints, version, undo: null };
      }
      return withDraftAction(session, { type: 'replace_surface', literal: action.literal }, { undo: true });
    }
    case 'insert_literal':
      return withDraftAction(session, { type: 'insert_literal', literal: action.literal }, { undo: true });
    case 'toggle_lock': {
      if (!session.draft) return session;
      const result = toggleLockKeepingSpan(session.draft, action.pos);
      if (!result.ok) return session;
      const width = result.draft.selection?.width ?? 0;
      const constraints = fitConstraintsToSpan(
        session.constraints,
        width,
        result.draft.slots,
        result.draft.selection,
      );
      // 鎖定唔開新 undo（CONTEXT 句稿復原）
      return commit(session, { draft: result.draft, constraints });
    }
    case 'clear_locks': {
      if (!session.draft) return session;
      if (!session.draft.slots.some((slot) => slot.locked)) return session;
      const slots = session.draft.slots.map((slot) => (
        slot.locked ? { ...slot, locked: false } : slot
      ));
      const draft = {
        ...session.draft,
        slots,
        selection: null,
        surface: slots.map((slot) => slot.surface).join(''),
      };
      // 清鎖定唔開 undo（同單擊鎖）
      return commit(session, { draft, constraints: session.constraints });
    }
    case 'choose_reading':
      // 只改讀音唔開新 undo
      return withDraftAction(session, {
        type: 'choose_reading',
        pos: action.pos,
        jyutping: action.jyutping,
        code: action.code,
      });
    case 'set_slot_manual':
      return withDraftAction(session, {
        type: 'set_slot_manual',
        pos: action.pos,
        surface: action.surface,
        code: action.code,
      }, { undo: true });
    case 'apply_span_input':
      return withDraftAction(session, {
        type: 'apply_span_input',
        selectionVersion: action.selectionVersion,
        slots: action.slots,
        constraints: action.constraints,
      }, { undo: true });
    case 'apply_candidate':
      return withDraftAction(session, {
        type: 'apply_candidate',
        selectionVersion: action.selectionVersion,
        literal: action.literal,
        jyutping: action.jyutping,
        code: action.code,
        relaxationId: action.relaxationId,
      }, { undo: true });
    case 'apply_relaxation': {
      if (!session.draft?.selection) return session;
      if (action.selectionVersion !== session.version) return session;
      const { start } = session.draft.selection;
      const remapped = action.plan.slots.map((slot) => ({ ...slot, pos: slot.pos + start }));
      const nextDraft = lineDraftReducer(session.draft, {
        type: 'apply_relaxation',
        selectionVersion: session.draft.version,
        relaxationId: action.relaxationId,
        constraints: remapped,
      });
      if (nextDraft === session.draft) return session;
      let constraints: ConstraintsUI = {
        ...session.constraints,
        mode: action.plan.mode,
        semanticIntent: action.plan.semanticIntent,
      };
      // remove_code：碼檔必須跟建議 plan，否則 derive 用 same_tone 會重注碼
      if (action.kind === 'remove_code') {
        const codeNext = codeConstraintAfterRemoveCode(action.plan.slots, action.plan.width);
        constraints = {
          ...constraints,
          codeConstraint: codeNext.mode,
          explicitCode: codeNext.explicit,
        };
      }
      return commit(session, { draft: nextDraft, constraints }, { undo: true, syncPhoneme: false });
    }
    case 'set_mode': {
      if (session.constraints.mode === action.mode) return session;
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, mode: action.mode },
      });
    }
    case 'set_semantic': {
      if (session.constraints.semanticIntent === action.semanticIntent) return session;
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, semanticIntent: action.semanticIntent },
      });
    }
    case 'set_code_constraint': {
      let explicitCode = session.constraints.explicitCode;
      if (action.mode === 'explicit' && session.draft?.selection) {
        explicitCode = sameToneCodePattern(session.draft.slots, session.draft.selection);
      }
      return commit(session, {
        draft: session.draft,
        constraints: {
          ...session.constraints,
          codeConstraint: action.mode,
          explicitCode,
        },
      });
    }
    case 'set_explicit_code': {
      const width = session.draft?.selection?.width ?? 0;
      const explicitCode = width > 0
        ? sanitizeExplicitCode(action.raw, width)
        : action.raw.replace(/[^\d?]/g, '');
      if (explicitCode === session.constraints.explicitCode) return session;
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, explicitCode },
      });
    }
    case 'set_rhyme_picks':
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, rhymePicks: action.picks },
      });
    case 'set_initial_picks':
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, initialPicks: action.picks },
      });
    case 'set_rhyme_ref':
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, rhymeRef: action.value },
      });
    case 'set_initial_ref':
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, initialRef: action.value },
      });
    case 'merge_ref_readings': {
      const refReadings = { ...session.constraints.refReadings, ...action.readings };
      return commit(session, {
        draft: session.draft,
        constraints: { ...session.constraints, refReadings },
      });
    }
    case 'apply_draft_action':
      return withDraftAction(session, action.action);
    case 'clear': {
      if (!session.draft) return session;
      return {
        draft: null,
        constraints: defaultConstraintsUI(),
        version: session.version + 1,
        undo: snap(session),
      };
    }
    case 'undo': {
      if (!session.undo) return session;
      const restored = session.undo;
      const version = session.version + 1;
      let draft = restored.draft;
      if (draft) {
        draft = syncPhonemeFromConstraints(draft, restored.constraints);
        draft = alignVersion(draft, version)!;
      }
      return {
        draft,
        constraints: restored.constraints,
        version,
        undo: null,
      };
    }
    default:
      return session;
  }
}

/**
 * Page 用：單次 toggle（validate + apply 同一結果，唔 double-toggle）。
 * 成功後 caller 應即時 sessionRef.current = result.session。
 */
export function sessionToggleLock(session: WorkbenchSession, pos: number): ToggleLockSessionResult {
  if (!session.draft) return { ok: false, reason: 'no_draft', session };
  const result = toggleLockKeepingSpan(session.draft, pos);
  if (!result.ok) return { ok: false, reason: result.reason, session };
  const width = result.draft.selection?.width ?? 0;
  const constraints = fitConstraintsToSpan(
    session.constraints,
    width,
    result.draft.slots,
    result.draft.selection,
  );
  return { ok: true, session: commit(session, { draft: result.draft, constraints }) };
}
