import type { CodeConstraintMode } from '../code-constraint.ts';
import type { RelaxationKind, ReplacementPlanV1 } from '../contracts.ts';
import type { LineDraft, LineDraftAction } from '../line-draft.ts';
import type { PhonemeDimPicks } from '../replacement-span.ts';

/** 本次替換條件 UI 真相 — 與 LineDraft 正交，同屬 WorkbenchSession。 */
export interface ConstraintsUI {
  mode: ReplacementPlanV1['mode'];
  semanticIntent: ReplacementPlanV1['semanticIntent'];
  codeConstraint: CodeConstraintMode;
  explicitCode: string;
  rhymePicks: PhonemeDimPicks;
  initialPicks: PhonemeDimPicks;
  rhymeRef: string;
  initialRef: string;
  /** 參考字 → 第一讀音（序列化用 plain object） */
  refReadings: Record<string, string>;
}

/** 可 undo／persist 嘅 session 快照（唔含 version 指針語意外嘅 paging）。 */
export interface SessionSnapshot {
  draft: LineDraft | null;
  constraints: ConstraintsUI;
}

/**
 * 句格工作台唯一 state root（對外 B）。
 * 對內 draft ∥ constraints 分檔處理（C）。
 */
export interface WorkbenchSession extends SessionSnapshot {
  version: number;
  undo: SessionSnapshot | null;
}

export type SessionPaging = {
  offset: number;
  limit: number;
};

export type SessionAction =
  | { type: 'create_from_parsed'; draft: LineDraft }
  | { type: 'replace_surface'; literal: string }
  | { type: 'insert_literal'; literal: string }
  | { type: 'toggle_lock'; pos: number }
  | { type: 'choose_reading'; pos: number; jyutping: string; code: string }
  | { type: 'set_slot_manual'; pos: number; surface: string; code?: string }
  | {
      type: 'apply_span_input';
      selectionVersion: number;
      slots: Array<{ surface: string; reading?: string; code?: string }>;
      constraints: import('../contracts.ts').WorkbenchSlotConstraintV1[];
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
      kind: RelaxationKind;
      plan: ReplacementPlanV1;
    }
  | { type: 'set_mode'; mode: ReplacementPlanV1['mode'] }
  | { type: 'set_semantic'; semanticIntent: ReplacementPlanV1['semanticIntent'] }
  | { type: 'set_code_constraint'; mode: CodeConstraintMode }
  | { type: 'set_explicit_code'; raw: string }
  | { type: 'set_rhyme_picks'; picks: PhonemeDimPicks }
  | { type: 'set_initial_picks'; picks: PhonemeDimPicks }
  | { type: 'set_rhyme_ref'; value: string }
  | { type: 'set_initial_ref'; value: string }
  | { type: 'merge_ref_readings'; readings: Record<string, string> }
  | { type: 'apply_draft_action'; action: LineDraftAction }
  | { type: 'clear' }
  | { type: 'undo' };

export type ToggleLockSessionResult =
  | { ok: true; session: WorkbenchSession }
  | { ok: false; reason: 'no_surface' | 'no_draft'; session: WorkbenchSession };
