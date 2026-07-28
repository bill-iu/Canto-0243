/**
 * Preferred / authoritative single-char readings — shared by F1 code filter + pure digit.
 */
import { compareAuthoritativeReadings, pronRankSortValueForWord } from '../../ranking.ts';
import { getWordCode, getWordText, type WordRow } from '../word-row.ts';

export function groupCandidatesByChar(candidates: WordRow[]): Map<string, WordRow[]> {
  const grouped = new Map<string, WordRow[]>();
  for (const word of candidates) {
    const char = getWordText(word);
    const list = grouped.get(char) ?? [];
    list.push(word);
    grouped.set(char, list);
  }
  return grouped;
}

export function preferredPronunciationRows(rows: WordRow[]): WordRow[] {
  if (!rows.length) {
    return [];
  }
  const ranked = rows.map((word) => ({
    rank: pronRankSortValueForWord(getWordText(word), String(word.jyutping ?? '')),
    word,
  }));
  const best = Math.min(...ranked.map((r) => r.rank));
  return ranked.filter((r) => r.rank === best).map((r) => r.word);
}

/** Best-rank ∩ code hit → one display row (pron → essay → !aa → jyut). */
export function pickAuthoritativeAmong(rows: WordRow[]): WordRow | null {
  if (!rows.length) return null;
  let best = rows[0]!;
  for (let i = 1; i < rows.length; i++) {
    const cur = rows[i]!;
    if (
      compareAuthoritativeReadings(
        { char: getWordText(cur), jyutping: String(cur.jyutping ?? '') },
        { char: getWordText(best), jyutping: String(best.jyutping ?? '') },
      ) < 0
    ) {
      best = cur;
    }
  }
  return best;
}

/**
 * 單 digit 純碼：每字面只以該字全部讀音中最佳 pron_rank 比碼；命中後權威序揀一列。
 * allRowsForHitChars 必須含字面全部 length=1 讀音（唔可以只係碼命中列）。
 */
export function filterSingleDigitToPreferredReadings(
  allRowsForHitChars: WordRow[],
  codeVariants: ReadonlySet<string>,
): WordRow[] {
  if (!allRowsForHitChars.length) return [];
  const out: WordRow[] = [];
  for (const group of groupCandidatesByChar(allRowsForHitChars).values()) {
    const preferred = preferredPronunciationRows(group);
    const matching = preferred.filter((word) => codeVariants.has(getWordCode(word) || ''));
    const picked = pickAuthoritativeAmong(matching);
    if (picked) out.push(picked);
  }
  return out;
}
