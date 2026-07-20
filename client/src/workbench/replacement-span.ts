import type { WorkbenchSlotConstraintV1 } from './contracts.ts';
import type { LineDraft, LineSelection, LineSlot } from './line-draft.ts';

/** Derived replacement span from 字位鎖定 (bounding box of locked slots). */
export function replacementSpanFromLocks(slots: readonly LineSlot[]): LineSelection | null {
  let start = -1;
  let end = -1;
  for (let i = 0; i < slots.length; i += 1) {
    if (!slots[i]?.locked) continue;
    if (start < 0) start = i;
    end = i;
  }
  if (start < 0 || end < start) return null;
  const width = end - start + 1;
  if (width < 1 || width > 4) return null;
  return { start, width };
}

export type ToggleLockFailure = 'no_surface' | 'span_too_wide';

export type ToggleLockResult =
  | { ok: true; draft: LineDraft }
  | { ok: false; reason: ToggleLockFailure; draft: LineDraft };

/** Click-toggle 字位鎖定; syncs draft.selection to 替換段; rejects span > 4. */
export function toggleLockKeepingSpan(draft: LineDraft, pos: number): ToggleLockResult {
  const current = draft.slots[pos];
  if (!current) return { ok: false, reason: 'no_surface', draft };
  // 有字面或有碼先可鎖（純碼格）；真正空白拒鎖
  if (!current.locked && !current.surface && !current.code) {
    return { ok: false, reason: 'no_surface', draft };
  }

  const slots = draft.slots.slice();
  slots[pos] = { ...current, locked: !current.locked };
  const span = replacementSpanFromLocks(slots);
  if (slots.some((slot) => slot.locked) && !span) {
    return { ok: false, reason: 'span_too_wide', draft };
  }

  return {
    ok: true,
    draft: {
      ...draft,
      slots,
      selection: span,
      surface: slots.map((slot) => slot.surface).join(''),
    },
  };
}

export interface PhonemeDimPicks {
  whole: boolean;
  head: boolean;
  tail: boolean;
  /** 0-based offsets within span that are neither head-only nor tail-only intents — middles. */
  middles: number[];
}

export function emptyPhonemeDimPicks(): PhonemeDimPicks {
  return { whole: false, head: false, tail: false, middles: [] };
}

export function spanPositionOptions(width: number): Array<{ key: 'head' | 'tail' | number; label: string }> {
  if (width < 1) return [];
  if (width === 1) return [{ key: 'head', label: '呢個字' }];
  const options: Array<{ key: 'head' | 'tail' | number; label: string }> = [
    { key: 'head', label: '頭字' },
  ];
  for (let offset = 1; offset <= width - 2; offset += 1) {
    options.push({ key: offset, label: `第 ${offset + 1} 字` });
  }
  options.push({ key: 'tail', label: '尾字' });
  return options;
}

function offsetsFromPicks(picks: PhonemeDimPicks, width: number): number[] {
  if (picks.whole) {
    return Array.from({ length: width }, (_, i) => i);
  }
  const out = new Set<number>();
  if (picks.head) out.add(0);
  if (picks.tail && width > 0) out.add(width - 1);
  for (const mid of picks.middles) {
    if (mid > 0 && mid < width - 1) out.add(mid);
  }
  return [...out].sort((a, b) => a - b);
}

export function phonemeCheckedOffsets(picks: PhonemeDimPicks, width: number): number[] {
  return offsetsFromPicks(picks, width);
}

/** Drop invalid middle picks after span width changes; keep head/tail/whole. */
export function sanitizePhonemeDimPicks(picks: PhonemeDimPicks, width: number): PhonemeDimPicks {
  if (width <= 0) return emptyPhonemeDimPicks();
  if (picks.whole) return { whole: true, head: false, tail: false, middles: [] };
  return {
    whole: false,
    head: picks.head,
    tail: picks.tail,
    middles: picks.middles.filter((mid) => mid > 0 && mid < width - 1),
  };
}

function slotAnchor(
  slot: LineSlot | undefined,
  refChar: string | undefined,
  refReadings: ReadonlyMap<string, string>,
): { ref: string; refJyutping: string } | null {
  if (refChar && refChar !== '?' ) {
    const jp = refReadings.get(refChar);
    if (jp) return { ref: refChar, refJyutping: jp };
    return null;
  }
  const surface = slot?.surface;
  const reading = slot?.reading;
  if (!surface || surface === '?' || !reading) return null;
  return { ref: surface, refJyutping: reading };
}

export function buildPhonemeAnchors(
  span: LineSelection,
  slots: readonly LineSlot[],
  rhyme: PhonemeDimPicks,
  initial: PhonemeDimPicks,
  rhymeRefChars: string[] | null = null,
  initialRefChars: string[] | null = null,
  refReadings: ReadonlyMap<string, string> = new Map(),
): WorkbenchSlotConstraintV1[] {
  const anchors: WorkbenchSlotConstraintV1[] = [];
  const rhymeOff = offsetsFromPicks(rhyme, span.width);
  const initialOff = offsetsFromPicks(initial, span.width);

  rhymeOff.forEach((offset, index) => {
    const resolved = slotAnchor(
      slots[span.start + offset],
      rhymeRefChars?.[index],
      refReadings,
    );
    if (!resolved) return;
    anchors.push({ pos: span.start + offset, kind: 'final_anchor', ...resolved });
  });
  initialOff.forEach((offset, index) => {
    const resolved = slotAnchor(
      slots[span.start + offset],
      initialRefChars?.[index],
      refReadings,
    );
    if (!resolved) return;
    anchors.push({ pos: span.start + offset, kind: 'initial_anchor', ...resolved });
  });
  return anchors;
}

export function withPhonemeAnchors(draft: LineDraft, anchors: WorkbenchSlotConstraintV1[]): LineDraft {
  const constraints = draft.constraints
    .filter((item) => item.kind !== 'final_anchor' && item.kind !== 'initial_anchor')
    .concat(anchors);
  return {
    ...draft,
    constraints,
    version: draft.version + 1,
  };
}
