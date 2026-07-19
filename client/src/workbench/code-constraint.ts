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

/**
 * remove_code 放寬後：碼約束檔須跟建議 plan（否則 useMemo 會用「同音」重注碼，放寬無效）。
 * 無剩餘碼 → 不限定；有剩餘 → 指定碼（缺位填 ?）。
 */
export function codeConstraintAfterRemoveCode(
  planSlots: readonly WorkbenchSlotConstraintV1[],
  width: number,
): { mode: CodeConstraintMode; explicit: string } {
  if (width < 1) return { mode: 'off', explicit: '' };
  const byPos = new Map<number, string>();
  for (const slot of planSlots) {
    if (slot.kind !== 'code_digit' || !slot.digit || !/^\d$/.test(slot.digit)) continue;
    if (slot.pos < 0 || slot.pos >= width) continue;
    byPos.set(slot.pos, slot.digit);
  }
  if (byPos.size === 0) return { mode: 'off', explicit: '' };
  let explicit = '';
  for (let pos = 0; pos < width; pos += 1) {
    explicit += byPos.get(pos) ?? '?';
  }
  return { mode: 'explicit', explicit };
}
