import { useEffect, useState, type FormEvent } from 'react';
import { getWorkbenchCopy } from '../../../shared/workbench-i18n.mjs';
import { createLineDraft } from './line-draft.ts';
import { parseLineInput } from './line-input.ts';
import { parseSpanManual } from './manual-slot-input.ts';
import type { WorkbenchSessionCoordinator } from './useWorkbenchSessionCoordinator.ts';
import { consumeIngest } from './workbench-bridge.ts';

/** Owns text entry, bridge ingestion and manual-edit feedback; the page renders controls. */
export function useWorkbenchInput(
  active: boolean,
  coordinator: WorkbenchSessionCoordinator,
  copy: ReturnType<typeof getWorkbenchCopy>,
) {
  const [input, setInput] = useState('');
  const [message, setMessage] = useState('');
  const { session } = coordinator.model;
  const { actions } = coordinator;

  useEffect(() => {
    if (!active) return;
    const payload = consumeIngest(sessionStorage);
    if (!payload) return;
    if (payload.mode === 'insert') {
      if (!session.draft?.selection) {
        setMessage(copy.insertNoSpan);
        return;
      }
      actions.insertLiteral(payload.literal);
      setMessage(copy.inserted);
      return;
    }
    const parsed = parseLineInput(payload.literal);
    if (!parsed.ok || parsed.kind !== 'surface') {
      setMessage(copy.ingestInvalid);
      return;
    }
    if (session.draft) actions.replaceSurface(payload.literal);
    else actions.createDraft(createLineDraft(parsed));
    setMessage(copy.ingested);
  }, [active, actions, copy, session.draft]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const parsed = parseLineInput(input);
    if (!parsed.ok) {
      setMessage(parsed.error === 'too_long' ? copy.tooLong : copy.invalidInput);
      return;
    }
    actions.createDraft(createLineDraft(parsed));
    setMessage(parsed.kind === 'code' ? copy.createdCode
      : parsed.kind === 'mixed' ? copy.createdMixed : copy.createdSurface);
  };

  const handleSetSlotManual = (pos: number, surface: string, code?: string) => {
    actions.changeManualSlot(pos, surface, code ?? '');
    actions.reportSpanError('');
    setMessage(surface ? copy.manualSurface : copy.manualCode);
  };

  const handleClearSurfaces = () => {
    if (!session.draft) return;
    actions.clearDraft();
    actions.reportSpanError('');
    setMessage(copy.cleared);
  };

  const handleApplySpanInput = (parsed: Extract<ReturnType<typeof parseSpanManual>, { ok: true }>) => {
    if (!session.draft?.selection) {
      actions.reportSpanError(copy.spanRequired);
      return;
    }
    const slots = parsed.slots.map((slot, pos) => {
      const digit = parsed.constraints.find((item) => item.kind === 'code_digit' && item.pos === pos);
      return { surface: slot.surface, reading: slot.reading,
        code: slot.code || (digit as { digit?: string })?.digit };
    });
    actions.applySpanInput({ selectionVersion: session.version, slots, constraints: parsed.constraints });
    actions.reportSpanError('');
    setMessage(copy.spanApplied);
  };

  return { input, setInput, message, setMessage, submit,
    handleSetSlotManual, handleClearSurfaces, handleApplySpanInput };
}
