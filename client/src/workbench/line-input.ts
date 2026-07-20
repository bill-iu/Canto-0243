export interface UnresolvedLineSlot {
  surface: string;
  reading?: string;
  code?: string;
}

export type InputConstraint =
  | { pos: number; kind: 'code_digit'; digit: string }
  | { pos: number; kind: 'tone_class'; toneClass: 'ping' | 'ze' };

export type ParsedLineInput =
  | {
      ok: true;
      kind: 'surface' | 'code' | 'tone' | 'mixed';
      slots: UnresolvedLineSlot[];
      constraints: InputConstraint[];
    }
  | { ok: false; error: 'empty' | 'mixed' | 'too_long' };

const MAX_SLOTS = 64;
const TONE_RE = /^[平仄PpZz]+$/;
const DIGIT_RE = /^\d$/;
const PINGZE_CHAR_RE = /^[平仄PpZz]$/;
const WILDCARD_RE = /^[?_%]$/;

function slotFromChar(value: string): UnresolvedLineSlot {
  if (DIGIT_RE.test(value)) return { surface: '', code: value };
  if (WILDCARD_RE.test(value)) return { surface: '?' };
  return { surface: value };
}

export function parseLineInput(raw: string): ParsedLineInput {
  const input = raw.trim();
  if (!input) return { ok: false, error: 'empty' };

  const values = Array.from(input);
  if (values.length > MAX_SLOTS) return { ok: false, error: 'too_long' };

  if (/^\d+$/.test(input)) {
    return {
      ok: true,
      kind: 'code',
      slots: values.map((digit) => ({ surface: '', code: digit })),
      constraints: values.map((digit, pos) => ({ pos, kind: 'code_digit', digit })),
    };
  }

  if (TONE_RE.test(input)) {
    return {
      ok: true,
      kind: 'tone',
      slots: values.map(() => ({ surface: '' })),
      constraints: values.map((value, pos) => ({
        pos,
        kind: 'tone_class',
        toneClass: value === '平' || value.toLowerCase() === 'p' ? 'ping' : 'ze',
      })),
    };
  }

  const hasDigit = values.some((value) => DIGIT_RE.test(value));
  const hasPingze = values.some((value) => PINGZE_CHAR_RE.test(value));
  const hasWildcard = values.some((value) => WILDCARD_RE.test(value));
  // ponytail: 平仄第一期唔同漢字／數字／通配混
  if (hasPingze && values.some((value) => !PINGZE_CHAR_RE.test(value))) {
    return { ok: false, error: 'mixed' };
  }

  if (!hasDigit && !hasWildcard) {
    return {
      ok: true,
      kind: 'surface',
      slots: values.map((surface) => ({ surface })),
      constraints: [],
    };
  }

  if (!hasDigit && hasWildcard) {
    return {
      ok: true,
      kind: 'surface',
      slots: values.map((value) => slotFromChar(value)),
      constraints: [],
    };
  }

  const slots: UnresolvedLineSlot[] = [];
  const constraints: InputConstraint[] = [];
  values.forEach((value, pos) => {
    if (DIGIT_RE.test(value)) {
      slots.push({ surface: '', code: value });
      constraints.push({ pos, kind: 'code_digit', digit: value });
      return;
    }
    slots.push(slotFromChar(value));
  });

  return { ok: true, kind: 'mixed', slots, constraints };
}
