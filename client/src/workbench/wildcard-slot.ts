/** 搜尋／工作台通配符：字面不限；畫布統一顯示 `?`。 */
export const WILDCARD_SURFACE = '?';

const WILDCARD_INPUT = new Set(['?', '_', '%']);

export function isWildcardChar(ch: string): boolean {
  return WILDCARD_INPUT.has(ch);
}

export function isWildcardSurface(surface: string | undefined): boolean {
  return surface === WILDCARD_SURFACE;
}

/** 句格／參考串用：有字面且非通配。 */
export function isHanSurface(surface: string | undefined): boolean {
  return Boolean(surface) && !isWildcardSurface(surface);
}

export function normalizeWildcardChar(ch: string): string {
  return isWildcardChar(ch) ? WILDCARD_SURFACE : ch;
}
