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
      kind: 'surface' | 'code' | 'tone';
      slots: UnresolvedLineSlot[];
      constraints: InputConstraint[];
    }
  | { ok: false; error: 'empty' | 'mixed' | 'too_long' };

const MAX_SLOTS = 64;

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

  if (/\d/.test(input)) return { ok: false, error: 'mixed' };

  if (/^[平仄PpZz]+$/.test(input)) {
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

  return {
    ok: true,
    kind: 'surface',
    slots: values.map((surface) => ({ surface })),
    constraints: [],
  };
}
