import type { WorkbenchSlotConstraintV1 } from './contracts.ts';
import type { LineSelection, LineSlot } from './line-draft.ts';

/** 工作台碼約束檔 — CONTEXT.md */
export type CodeConstraintMode = 'same_tone' | 'off' | 'explicit';

export function sameToneCodePattern(
  slots: readonly LineSlot[],
  span: LineSelection,
): string {
  let out = '';
  for (let offset = 0; offset < span.width; offset += 1) {
    const slot = slots[span.start + offset];
    out += slot?.locked && slot.code && /^\d$/.test(slot.code) ? slot.code : '?';
  }
  return out;
}

export function sanitizeExplicitCode(raw: string, width: number): string {
  if (width < 1) return '';
  return Array.from(raw).filter((ch) => /^[\d?]$/.test(ch)).slice(0, width).join('');
}

export function padExplicitCode(raw: string, width: number): string {
  const clipped = sanitizeExplicitCode(raw, width);
  if (clipped.length >= width) return clipped;
  return clipped + '?'.repeat(width - clipped.length);
}

export function buildCodeDigitSlots(
  mode: CodeConstraintMode,
  slots: readonly LineSlot[],
  span: LineSelection,
  explicit: string,
): WorkbenchSlotConstraintV1[] {
  if (mode === 'off') return [];

  if (mode === 'same_tone') {
    const out: WorkbenchSlotConstraintV1[] = [];
    for (let offset = 0; offset < span.width; offset += 1) {
      const slot = slots[span.start + offset];
      if (!slot?.locked || !slot.code || !/^\d$/.test(slot.code)) continue;
      out.push({ pos: offset, kind: 'code_digit', digit: slot.code });
    }
    return out;
  }

  const pattern = padExplicitCode(explicit, span.width);
  const out: WorkbenchSlotConstraintV1[] = [];
  for (let offset = 0; offset < span.width; offset += 1) {
    const digit = pattern[offset];
    if (!digit || digit === '?' || !/^\d$/.test(digit)) continue;
    out.push({ pos: offset, kind: 'code_digit', digit });
  }
  return out;
}

export function planHasQueryableSlots(
  slots: readonly WorkbenchSlotConstraintV1[],
  semanticSeed: string,
  semanticIntent: 'ranked' | 'direct_only' | 'off',
): boolean {
  if (slots.length > 0) return true;
  return Boolean(semanticSeed && semanticIntent !== 'off');
}
