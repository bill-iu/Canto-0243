/** 平仄串列查詢 — port of app/services/ping_zak.py */
import { getCodeVariants } from './code-variants.ts';
import type { ParsedQuery, UnmatchedQuery } from './query-types.ts';
import { QueryKind } from './query-kind.ts';

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
