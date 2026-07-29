/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { compareSearchResults, literalPriorityCompare } from '../ranking.ts';
import { getRhymeProfile } from '../rhyme-profile-context.ts';
import { throwIfSearchCancelled, yieldToMainThread, type ShouldCancel } from '../search-cancel.ts';
import { applyMatchSpec } from './filters.ts';
import { getCandidatesForLength, getLengthMaskCandidates } from './sources.ts';
import { getPhonemeAnchorCandidates } from './phoneme-index.ts';
import {
  buildRequiredCodes,
  matchesCodePositions,
} from './filters/f1-slot-code.ts';
import { canonicalizeLegacyMatchSpec, type CanonicalMatchSpec } from './canonical.ts';
import { exactFinalRankKey, exactFinalSlotOptions } from './rhyme-exact-rank.ts';
import type { MatchSpec } from './spec.ts';
import { getWordCode, type WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);
const PHONEME_ANCHOR_KINDS = new Set(['final_anchor', 'initial_anchor']);

async function cooperativeSort(
  rows: WordRow[],
  compare: (a: WordRow, b: WordRow) => number,
  shouldCancel?: ShouldCancel,
  cooperative = false,
): Promise<WordRow[]> {
  if (!cooperative) return [...rows].sort(compare);
  const chunkSize = 2048;
  let chunks: WordRow[][] = [];
  for (let start = 0; start < rows.length; start += chunkSize) {
    chunks.push(rows.slice(start, start + chunkSize).sort(compare));
    throwIfSearchCancelled(shouldCancel);
    await yieldToMainThread();
  }
  while (chunks.length > 1) {
    const merged: WordRow[][] = [];
    for (let index = 0; index < chunks.length; index += 2) {
      const left = chunks[index]!;
      const right = chunks[index + 1];
      if (!right) {
        merged.push(left);
        continue;
      }
      const next: WordRow[] = [];
      let l = 0;
      let r = 0;
      let mergedRows = 0;
      while (l < left.length && r < right.length) {
        next.push(compare(left[l]!, right[r]!) <= 0 ? left[l++]! : right[r++]!);
        mergedRows += 1;
        if (mergedRows % 4096 === 0) {
          throwIfSearchCancelled(shouldCancel);
          await yieldToMainThread();
        }
      }
      while (l < left.length) {
        next.push(left[l++]!);
        mergedRows += 1;
        if (mergedRows % 4096 === 0) {
          throwIfSearchCancelled(shouldCancel);
          await yieldToMainThread();
        }
      }
      while (r < right.length) {
        next.push(right[r++]!);
        mergedRows += 1;
        if (mergedRows % 4096 === 0) {
          throwIfSearchCancelled(shouldCancel);
          await yieldToMainThread();
        }
      }
      merged.push(next);
      throwIfSearchCancelled(shouldCancel);
      await yieldToMainThread();
    }
    chunks = merged;
  }
  return chunks[0] ?? [];
}

function firstPhonemeAnchorSlot(spec: CanonicalMatchSpec): CanonicalMatchSpec['slots'][number] | null {
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') {
      return slot;
    }
  }
  return null;
}

function countPhonemeAnchorSlots(spec: CanonicalMatchSpec): number {
  let n = 0;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') n += 1;
  }
  return n;
}

/** Early sync shrink after inverted-index load (code digits on ?30+人 etc.). */
function filterByRequiredCodes(
  rows: WordRow[],
  spec: CanonicalMatchSpec,
  mode: string,
): WordRow[] {
  const required = buildRequiredCodes(spec);
  if (!required.some((r) => r != null)) {
    return rows;
  }
  return rows.filter((w) => matchesCodePositions(getWordCode(w), required, mode));
}

function shouldUseMaskCandidates(spec: CanonicalMatchSpec): boolean {
  // ponytail: only when mask has fixed CJK literals (not pure ?? / digit masks)
  if (!spec.mask || spec.compound || spec.equals_span) {
    return false;
  }
  // Pure ? or code-digit masks have no char GLOB value — use length+code path instead
  // (fixes 3$漢4 etc. loading all width-N rows via GLOB ??)
  if (!/[^\d?]/.test(spec.mask)) {
    return false;
  }
  return true;
}

/** True when filter needs the full length bucket (desktop word_cache parity; no 2000 cap). */
function specNeedsFullLengthBucket(spec: CanonicalMatchSpec): boolean {
  return (spec.slots ?? []).some(
    (s) => JYUTPING_LETTER_KINDS.has(s.kind) || PHONEME_ANCHOR_KINDS.has(s.kind),
  );
}

/**
 * Complete width-digit code for SQL IN variants — from ctx/prefix, pure digit mask, or dense code_digit slots.
 * Partial codes (not every position) return null so phoneme path can take unlimited bucket.
 */
export function narrowingCodeFromSpec(spec: CanonicalMatchSpec, ctxCode?: string | null): string | null {
  /** PR-A: dense code only from ctx / mask digits / code_digit slots — never code_prefix. */
  if (ctxCode && /^\d+$/.test(ctxCode) && ctxCode.length === spec.width) {
    return ctxCode;
  }
  if (spec.mask && spec.mask.length === spec.width && /^\d+$/.test(spec.mask)) {
    return spec.mask;
  }
  const digits: Array<string | null> = Array.from({ length: spec.width }, () => null);
  if (spec.mask && spec.mask.length === spec.width) {
    for (let i = 0; i < spec.width; i++) {
      const ch = spec.mask[i]!;
      if (/\d/.test(ch)) {
        digits[i] = ch;
      }
    }
  }
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'code_digit' && slot.pos >= 0 && slot.pos < spec.width && slot.value != null) {
      digits[slot.pos] = String(slot.value);
    }
  }
  if (digits.every((d) => d != null && /^\d$/.test(d))) {
    return digits.join('');
  }
  return null;
}

export type ExecuteMatchSpecContext = {
  db: Database;
  mode: string;
  limit: number;
  offset: number;
  code?: string | null;
  shouldCancel?: ShouldCancel;
};

/** Filter all matching rows — port of PositionMatchEngine.match (no sort/page). */
export async function filterMatchSpecRows(
  input: CanonicalMatchSpec | MatchSpec,
  ctx: Pick<ExecuteMatchSpecContext, 'db' | 'mode' | 'code' | 'shouldCancel'>,
): Promise<WordRow[]> {
  const spec = 'candidate_scope' in input ? input : canonicalizeLegacyMatchSpec(input);
  if (!spec || spec.width === 0) {
    return [];
  }
  throwIfSearchCancelled(ctx.shouldCancel);
  if (spec.equals_span || spec.compound) {
    return applyMatchSpec(spec, [], ctx.db, ctx.mode, ctx.shouldCancel);
  }
  const hasPositionFilters =
    Boolean(spec.mask) ||
    (spec.slots ?? []).some(
      (s) =>
        s.kind === 'final_anchor' ||
        s.kind === 'initial_anchor' ||
        JYUTPING_LETTER_KINDS.has(s.kind),
    );
  if (!hasPositionFilters) {
    return [];
  }

  // C1: full-width code first (SQL IN); else phoneme anchors prefer runtime inverted index
  const code = narrowingCodeFromSpec(spec, ctx.code);
  let candidates: WordRow[];
  let fromPhonemeIndex = false;
  if (shouldUseMaskCandidates(spec) && spec.mask) {
    [candidates] = await getLengthMaskCandidates(ctx.db, spec.width, spec.mask, {
      code,
      mode: ctx.mode,
    });
  } else {
    // Prefer phoneme index whenever anchors exist — even with dense code digits.
    // Dense-code + LIMIT otherwise truncates before phoneme filtering (workbench 同韻／同聲).
    const phonemeSlot = firstPhonemeAnchorSlot(spec);
    let indexed: WordRow[] | null = null;
    if (phonemeSlot) {
      const constraint = phonemeSlot.kind === 'final_anchor' ? 'final' : 'initial';
      indexed = await getPhonemeAnchorCandidates(
        ctx.db,
        spec.width,
        phonemeSlot.pos,
        String(phonemeSlot.value ?? ''),
        constraint,
      );
    }
    if (indexed) {
      candidates = filterByRequiredCodes(indexed, spec, ctx.mode);
      fromPhonemeIndex = countPhonemeAnchorSlots(spec) === 1;
    } else {
      // Dense full-width code must not use LIMIT+ORDER BY char — alpha truncation
      // drops high-freq hits (repro: 貪婪→30 pool ~3k, 金錢 essay-high but late char order).
      const codePositions = code
        ? undefined
        : buildRequiredCodes(spec)
            .map((digit, pos) => (digit != null ? { pos, digit } : null))
            .filter((x): x is { pos: number; digit: string } => x != null);
      const minimal = Boolean(
        spec.candidate_scope === 'complete'
        && !(spec.slots ?? []).length
        && spec.mask
        && [...spec.mask].every((char) => char === '?' || char === '_' || char === '%'),
      );
      [candidates] = await getCandidatesForLength(ctx.db, spec.width, {
        code,
        mode: ctx.mode,
        unlimited:
          specNeedsFullLengthBucket(spec)
          || spec.candidate_scope === 'complete'
          || Boolean(code)
          || Boolean(codePositions?.length),
        codePositions,
        minimal,
      });
    }
  }
  throwIfSearchCancelled(ctx.shouldCancel);
  return applyMatchSpec(spec, candidates, ctx.db, ctx.mode, ctx.shouldCancel, {
    phonemeIndexPrefiltered: fromPhonemeIndex,
  });
}

/** Filter + sort + page; `total` is the full sorted pool size (ADR-0064). */
async function executeCanonicalPage(
  spec: CanonicalMatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<{ rows: WordRow[]; total: number }> {
  if (!spec || spec.width === 0) {
    return { rows: [], total: 0 };
  }
  const shouldYield = spec.candidate_scope === 'complete';
  if (spec.phoneme_alternatives) {
    // Dual path materializes a truncated union; count that union after paging window math.
    const unpagedLimit = Math.max(ctx.limit + ctx.offset, ctx.limit) + 500;
    const base = {
      db: ctx.db,
      mode: ctx.mode,
      code: ctx.code ?? null,
      shouldCancel: ctx.shouldCancel,
    };
    const initialSpec = spec.phoneme_alternatives.initial;
    const finalSpec = spec.phoneme_alternatives.final;
    const initialRows = (await cooperativeSort(
      await filterMatchSpecRows(initialSpec, base),
      compareSearchResults,
      ctx.shouldCancel,
      shouldYield,
    )).slice(0, unpagedLimit);
    throwIfSearchCancelled(ctx.shouldCancel);
    const finalRows = (await cooperativeSort(
      await filterMatchSpecRows(finalSpec, base),
      compareSearchResults,
      ctx.shouldCancel,
      shouldYield,
    )).slice(0, unpagedLimit);
    const tagged: WordRow[] = [
      ...initialRows.map((row) => ({ ...row, anchor_dimension: 'initial' })),
      ...finalRows.map((row) => ({ ...row, anchor_dimension: 'final' })),
    ];
    const sorted = await cooperativeSort(
      tagged,
      compareSearchResults,
      ctx.shouldCancel,
      shouldYield,
    );
    return {
      rows: sorted.slice(ctx.offset, ctx.offset + ctx.limit),
      total: sorted.length,
    };
  }
  const filtered = await filterMatchSpecRows(spec, ctx);
  throwIfSearchCancelled(ctx.shouldCancel);
  const exactSlots =
    getRhymeProfile() !== 'exact' ? await exactFinalSlotOptions(spec, ctx.db) : [];
  const withExact = (cmp: (a: WordRow, b: WordRow) => number) =>
    exactSlots.length
      ? (a: WordRow, b: WordRow) => {
          const ra = exactFinalRankKey(a, exactSlots);
          const rb = exactFinalRankKey(b, exactSlots);
          return ra - rb || cmp(a, b);
        }
      : cmp;
  let sorted: WordRow[];
  const literalPositions = [...spec.mask]
    .map((char, pos) => (/[\p{Script=Han}]/u.test(char) ? [pos, char] as [number, string] : null))
    .filter((item): item is [number, string] => item != null);
  if (spec.ranking === 'literal_priority' && literalPositions.length) {
    sorted = await cooperativeSort(
      filtered,
      withExact((a, b) => literalPriorityCompare(a, b, literalPositions)),
      ctx.shouldCancel,
      shouldYield,
    );
  } else {
    sorted = await cooperativeSort(
      filtered,
      withExact(compareSearchResults),
      ctx.shouldCancel,
      shouldYield,
    );
  }
  return {
    rows: sorted.slice(ctx.offset, ctx.offset + ctx.limit),
    total: sorted.length,
  };
}

/** Legacy compatibility seam: normalize once, then execute the canonical value. */
export async function executeMatchSpecPage(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<{ rows: WordRow[]; total: number }> {
  return executeCanonicalPage(canonicalizeLegacyMatchSpec(spec), ctx);
}

/** Port of run_position_query_tracked — filter, sort, then page. */
export async function executeMatchSpec(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<WordRow[]> {
  return (await executeMatchSpecPage(spec, ctx)).rows;
}

/** Canonical execution entry. */
export async function executeCanonicalMatchSpecPage(
  spec: CanonicalMatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<{ rows: WordRow[]; total: number }> {
  return executeCanonicalPage(spec, ctx);
}
