import { parseLineInput, type ParsedLineInput } from './line-input.ts';

/** 單格手改：一字漢字，或一碼 `0–9`。本階段唔收 `?`。 */
export function parseManualCell(
  raw: string,
): { ok: true; surface: string; code?: string } | { ok: false } {
  const trimmed = raw.trim();
  if (!trimmed || trimmed.includes('?')) return { ok: false };
  const chars = Array.from(trimmed);
  if (chars.length !== 1) return { ok: false };
  const ch = chars[0]!;
  if (/^[0-9]$/.test(ch)) return { ok: true, surface: '', code: ch };
  if (/\p{Script=Han}/u.test(ch)) return { ok: true, surface: ch };
  return { ok: false };
}

/** 段手打：規則同工作台起句；長度須＝段寬。本階段唔收 `?`。 */
export function parseSpanManual(
  raw: string,
  width: number,
): Extract<ParsedLineInput, { ok: true }> | { ok: false; error: string } {
  if (raw.includes('?')) return { ok: false, error: 'no_wildcard' };
  const parsed = parseLineInput(raw);
  if (!parsed.ok) return { ok: false, error: parsed.error };
  if (parsed.slots.length !== width) return { ok: false, error: 'width' };
  return parsed;
}
