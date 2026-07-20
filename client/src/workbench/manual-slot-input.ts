import { parseLineInput, type ParsedLineInput } from './line-input.ts';
import {
  isWildcardChar,
  normalizeWildcardChar,
  WILDCARD_SURFACE,
} from './wildcard-slot.ts';

/** 單格手改：一字漢字、一碼 `0–9`、或一個通配符。 */
export function parseManualCell(
  raw: string,
): { ok: true; surface: string; code?: string } | { ok: false } {
  const trimmed = raw.trim();
  if (!trimmed) return { ok: false };
  const chars = Array.from(trimmed);
  if (chars.length !== 1) return { ok: false };
  const ch = chars[0]!;
  if (/^[0-9]$/.test(ch)) return { ok: true, surface: '', code: ch };
  if (isWildcardChar(ch)) return { ok: true, surface: WILDCARD_SURFACE };
  if (/\p{Script=Han}/u.test(ch)) return { ok: true, surface: ch };
  return { ok: false };
}

/** 段手打：規則同工作台起句；長度須＝段寬。 */
export function parseSpanManual(
  raw: string,
  width: number,
): Extract<ParsedLineInput, { ok: true }> | { ok: false; error: string } {
  const parsed = parseLineInput(raw);
  if (!parsed.ok) return { ok: false, error: parsed.error };
  if (parsed.slots.length !== width) return { ok: false, error: 'width' };
  return parsed;
}

/** 參考字串：空白＝跟原；非空長度須＝checkedCount；只收漢字與通配。 */
export function parsePhonemeRef(
  raw: string,
  checkedCount: number,
): { ok: true; chars: string[] | null } | { ok: false } {
  if (checkedCount < 1) return { ok: true, chars: null };
  const trimmed = raw.trim();
  if (!trimmed) return { ok: true, chars: null };
  const chars = Array.from(trimmed).map(normalizeWildcardChar);
  if (chars.length !== checkedCount) return { ok: false };
  if (chars.some((ch) => ch !== WILDCARD_SURFACE && !/\p{Script=Han}/u.test(ch))) {
    return { ok: false };
  }
  return { ok: true, chars };
}
