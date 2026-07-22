import {
  sameToneCodePattern,
  sanitizeExplicitCode,
} from '../code-constraint.ts';
import type { LineDraft, LineSelection, LineSlot } from '../line-draft.ts';
import { parsePhonemeRef } from '../manual-slot-input.ts';
import {
  buildPhonemeAnchors,
  emptyPhonemeDimPicks,
  phonemeCheckedOffsets,
  replacementSpanFromLocks,
  sanitizePhonemeDimPicks,
  withPhonemeAnchors,
} from '../replacement-span.ts';
import type { ConstraintsUI } from './types.ts';

function refMap(constraints: ConstraintsUI): Map<string, string> {
  return new Map(Object.entries(constraints.refReadings));
}

/** 由 constraintsUI 重寫 draft 上嘅韻／聲錨（單一寫入路徑）。 */
export function syncPhonemeFromConstraints(draft: LineDraft, constraints: ConstraintsUI): LineDraft {
  const span = draft.selection ?? replacementSpanFromLocks(draft.slots);
  if (!span) {
    return withPhonemeAnchors(draft, []);
  }
  const rhyme = sanitizePhonemeDimPicks(constraints.rhymePicks, span.width);
  const initial = sanitizePhonemeDimPicks(constraints.initialPicks, span.width);
  const rhymeParsed = parsePhonemeRef(constraints.rhymeRef, phonemeCheckedOffsets(rhyme, span.width).length);
  const initialParsed = parsePhonemeRef(
    constraints.initialRef,
    phonemeCheckedOffsets(initial, span.width).length,
  );
  return withPhonemeAnchors(
    draft,
    buildPhonemeAnchors(
      span,
      draft.slots,
      rhyme,
      initial,
      rhymeParsed.ok ? rhymeParsed.chars : null,
      initialParsed.ok ? initialParsed.chars : null,
      refMap(constraints),
    ),
  );
}

/** 段寬變更時裁剪 picks／explicit。 */
export function fitConstraintsToSpan(
  constraints: ConstraintsUI,
  width: number,
  slots: readonly LineSlot[],
  span: LineSelection | null,
): ConstraintsUI {
  const rhymePicks = width > 0
    ? sanitizePhonemeDimPicks(constraints.rhymePicks, width)
    : emptyPhonemeDimPicks();
  const initialPicks = width > 0
    ? sanitizePhonemeDimPicks(constraints.initialPicks, width)
    : emptyPhonemeDimPicks();
  let explicitCode = constraints.explicitCode;
  if (constraints.codeConstraint === 'explicit' && span && width > 0) {
    explicitCode = explicitCode.length === width
      ? sanitizeExplicitCode(explicitCode, width)
      : sameToneCodePattern(slots, span);
  }
  return { ...constraints, rhymePicks, initialPicks, explicitCode };
}
