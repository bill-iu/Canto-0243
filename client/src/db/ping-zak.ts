/** 平仄串列查詢 — port of app/services/ping_zak.py */
import { getCodeVariants } from './code-variants.ts';
import type { ParsedQuery, PingZeSerialQuery, UnmatchedQuery } from './query-types.ts';
import { QueryKind } from './query-kind.ts';
import { createMatchSpec, type MatchSpec } from './position-match/spec.ts';

export type PingZak = 'ping' | 'ze';

export type PingZeSubMode = 'm1' | 'm2' | 'm3';

export const PING_ZE_INVALID_HINT =
  '平仄串列查詢只接受 P（平）、Z（仄）與聲調數字 0–9；字面請改用缺字語法（如 ?+就=）。';

const PING_ZE_SLOT_RE = /^[PZ0-9?]+$/;
const HAS_PZ_RE = /[PZ]/;

const M02493_TO_0243: Record<string, string> = {
  '1': '3',
  '5': '5',
  '6': '2',
  '7': '3',
  '8': '4',
};

export function pingZakClass(codeDigit: string): PingZak {
  return codeDigit === '0' || codeDigit === '3' ? 'ping' : 'ze';
}

export function normalizePingZePattern(q: string): string {
  return q.toUpperCase();
}

export function normalizePzmode(mode?: string): PingZeSubMode {
  return mode === 'm2' || mode === 'm3' ? mode : 'm1';
}

export function digitSlotMatches(queryDigit: string, codeDigit: string, pzmode: PingZeSubMode = 'm1'): boolean {
  return getCodeVariants(queryDigit, pzmode).includes(codeDigit);
}

export function codeMatchesPingZePattern(code: string, pattern: string, pzmode: PingZeSubMode = 'm1'): boolean {
  const pat = normalizePingZePattern(pattern);
  if (code.length !== pat.length) {
    return false;
  }
  for (let i = 0; i < pat.length; i += 1) {
    const cd = code[i]!;
    const slot = pat[i]!;
    if (slot === 'P') {
      if (pingZakClass(cd) !== 'ping') return false;
    } else if (slot === 'Z') {
      if (pingZakClass(cd) !== 'ze') return false;
    } else if (/\d/.test(slot)) {
      if (!digitSlotMatches(slot, cd, pzmode)) return false;
    } else if (slot === '?') {
      continue;
    } else {
      return false;
    }
  }
  return true;
}

export function tryParsePingZeSerial(q: string, pzmode?: string): ParsedQuery | null {
  if (!q || !HAS_PZ_RE.test(q)) {
    return null;
  }
  if (!PING_ZE_SLOT_RE.test(q)) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: PING_ZE_INVALID_HINT } satisfies UnmatchedQuery;
  }
  return {
    kind: QueryKind.PING_ZE_SERIAL,
    raw_q: normalizePingZePattern(q),
    pzmode: normalizePzmode(pzmode),
  };
}

export function isPingZeSerialQuery(q: string, pzmode?: string): boolean {
  const parsed = tryParsePingZeSerial(q, pzmode);
  return parsed?.kind === QueryKind.PING_ZE_SERIAL;
}

export function slotLabel(slot: string, lang: 'zh' | 'en' = 'zh'): string {
  if (slot === 'P') {
    return lang === 'zh' ? '平' : 'ping (P)';
  }
  if (slot === 'Z') {
    return lang === 'zh' ? '仄' : 'ze (Z)';
  }
  const mapped = M02493_TO_0243[slot] ?? slot;
  if (lang === 'zh') {
    return mapped !== slot ? `與 ${slot} 同音（→${mapped}）` : `與 ${slot} 同音`;
  }
  return mapped !== slot ? `same tone as ${slot} (→${mapped})` : `same tone as ${slot}`;
}


function applyPingZeSlots(spec: MatchSpec, rawQ: string): void {
  const codeDigitPositions = new Set(
    (spec.slots ?? []).filter((slot) => slot.kind === 'code_digit').map((slot) => slot.pos),
  );
  const fixed = new Set(
    (spec.slots ?? [])
      .filter(
        (slot) =>
          slot.kind !== 'code_digit' &&
          slot.kind !== 'tone_class' &&
          !codeDigitPositions.has(slot.pos),
      )
      .map((slot) => slot.pos),
  );
  const codePositions = Array.from({ length: spec.width }, (_, pos) => pos).filter(
    (pos) => !fixed.has(pos),
  );
  const tokens = [...rawQ].filter((token) => /[PZ?0-9]/.test(token));
  tokens.forEach((token, index) => {
    if (token !== 'P' && token !== 'Z') return;
    const pos = codePositions[index];
    if (pos == null) return;
    spec.slots = (spec.slots ?? []).filter(
      (slot) => !(slot.pos === pos && slot.kind === 'code_digit'),
    );
    spec.mask = `${spec.mask.slice(0, pos)}?${spec.mask.slice(pos + 1)}`;
    (spec.slots ??= []).push({
      pos,
      kind: 'tone_class',
      value: token === 'P' ? 'ping' : 'ze',
    });
  });
}

/** Port of ping_zak.to_match_spec — buildBaseSpec breaks registry cycle. */
export function toMatchSpec(
  parsed: ParsedQuery,
  buildBaseSpec: (p: ParsedQuery) => MatchSpec | null,
): MatchSpec | null {
  if (parsed.kind !== QueryKind.PING_ZE_SERIAL) return null;
  const q = parsed as PingZeSerialQuery;
  if (q.base) {
    const spec = buildBaseSpec(q.base);
    if (!spec) return null;
    if (!spec.extra) spec.extra = {};
    spec.extra.code_mode = q.pzmode;
    applyPingZeSlots(spec, q.raw_q);
    return spec;
  }
  const spec = createMatchSpec(q.raw_q.length, { mask: '?'.repeat(q.raw_q.length) });
  if (!spec.extra) spec.extra = {};
  spec.extra.code_mode = q.pzmode;
  for (let pos = 0; pos < q.raw_q.length; pos += 1) {
    const token = q.raw_q[pos]!;
    if (token === 'P') {
      (spec.slots ??= []).push({ pos, kind: 'tone_class', value: 'ping' });
    } else if (token === 'Z') {
      (spec.slots ??= []).push({ pos, kind: 'tone_class', value: 'ze' });
    } else if (/\d/.test(token)) {
      (spec.slots ??= []).push({ pos, kind: 'code_digit', value: token });
    }
  }
  if (q.anchor) {
    spec.width += 1;
    spec.mask = '?'.repeat(spec.width);
    (spec.slots ??= []).push({
      pos: q.raw_q.length,
      kind: 'final_anchor',
      value: q.anchor,
    });
  }
  return spec;
}
