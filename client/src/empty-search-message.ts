export type SearchUiMode = '0243' | '02493' | 'synonym';

/** ponytail: PWA + desktop unified copy — 搵唔到 for all modes */
export function formatEmptySearchMessage(
  query: string,
  hint?: string | null,
  mode: SearchUiMode = '0243',
): { primary: string; secondary?: string } {
  if (hint) {
    return { primary: '搵唔到', secondary: hint };
  }
  const q = query.trim();
  const secondary =
    mode === 'synonym'
      ? '試試改用較短的詞、加上 = 查韻，或切換搜尋模式。'
      : undefined;
  return { primary: `搵唔到「${q}」。`, secondary };
}
