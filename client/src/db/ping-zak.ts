/** 平仄串列查詢 — port of app/services/ping_zak.py */
import { normalize02493Code } from './code-variants.ts';
import type { ParsedQuery, UnmatchedQuery } from './query-types.ts';
import { QueryKind } from './query-kind.ts';

export type PingZak = 'ping' | 'ze';

export const MATRIX_394052_MODE: string | null = 'm3';

export const PING_ZE_INVALID_HINT =
  '平仄串列查詢只接受 P（平）、Z（仄）與聲調數字 0–9；字面請改用缺字語法（如 ?+就=）。';

const PING_ZE_SLOT_RE = /^[PZ0-9]+$/i;
const HAS_PZ_RE = /[PZ]/i;

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

export function pingZeEffectiveMode(): 'm2' | string {
  if (MATRIX_394052_MODE) {
    return MATRIX_394052_MODE;
  }
  return 'm2';
}

export function pingZeModeRedirectHint(effective: string, lang: 'zh' | 'en' = 'zh'): string | null {
  if (MATRIX_394052_MODE && effective === MATRIX_394052_MODE) {
    return null;
  }
  if (lang === 'en') {
    return 'Ping–ze serial query switched to 02493 Mode (Strict)';
  }
  return '平仄串列查詢已切換至 02493模式（緊）';
}

export function digitSlotMatches(queryDigit: string, codeDigit: string): boolean {
  return normalize02493Code(queryDigit) === codeDigit;
}

export function codeMatchesPingZePattern(code: string, pattern: string): boolean {
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
      if (!digitSlotMatches(slot, cd)) return false;
    } else {
      return false;
    }
  }
  return true;
}

export function tryParsePingZeSerial(q: string): ParsedQuery | null {
  if (!q || !HAS_PZ_RE.test(q)) {
    return null;
  }
  if (!PING_ZE_SLOT_RE.test(q)) {
    return { kind: QueryKind.UNMATCHED, raw_q: q, hint: PING_ZE_INVALID_HINT } satisfies UnmatchedQuery;
  }
  return { kind: QueryKind.PING_ZE_SERIAL, raw_q: normalizePingZePattern(q) };
}

export function isPingZeSerialQuery(q: string): boolean {
  const parsed = tryParsePingZeSerial(q);
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