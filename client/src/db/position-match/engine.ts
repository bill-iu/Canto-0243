/**
 * executeMatchSpec — port of position_match/engine.py (MF-4)
 */
import type { Database } from '../sqljs.ts';
import { sortWordRows, literalPriorityCompare } from '../ranking.ts';
import { throwIfSearchCancelled, type ShouldCancel } from '../search-cancel.ts';
import { applyMatchSpec } from './filters.ts';
import { getCandidatesForLength, getLengthMaskCandidates } from './sources.ts';
import { getPhonemeAnchorCandidates } from './phoneme-index.ts';
import {
  buildRequiredCodes,
  matchesCodePositions,
} from './filters/f1-slot-code.ts';
import { getEqualsSpan, type MatchSpec, type SlotConstraint } from './spec.ts';
import { getWordCode, type WordRow } from './word-row.ts';

const JYUTPING_LETTER_KINDS = new Set(['rhyme_letters', 'syllable_letters', 'initial_letters']);
const PHONEME_ANCHOR_KINDS = new Set(['final_anchor', 'initial_anchor']);

function firstPhonemeAnchorSlot(spec: MatchSpec): SlotConstraint | null {
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') {
      return slot;
    }
  }
  return null;
}

function countPhonemeAnchorSlots(spec: MatchSpec): number {
  let n = 0;
  for (const slot of spec.slots ?? []) {
    if (slot.kind === 'final_anchor' || slot.kind === 'initial_anchor') n += 1;
  }
  return n;
}

/** Early sync shrink after inverted-index load (code digits on ?30+人 etc.). */
function filterByRequiredCodes(
  rows: WordRow[],
  spec: MatchSpec,
  mode: string,
): WordRow[] {
  const required = buildRequiredCodes(spec);
  if (!required.some((r) => r != null)) {
    return rows;
  }
  return rows.filter((w) => matchesCodePositions(getWordCode(w), required, mode));
}

function shouldUseMaskCandidates(spec: MatchSpec): boolean {
  // ponytail: only when mask has fixed CJK literals (not pure ?? / digit masks)
  if (!spec.mask || spec.compound_kind || getEqualsSpan(spec)) {
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
function specNeedsFullLengthBucket(spec: MatchSpec): boolean {
  return (spec.slots ?? []).some(
    (s) => JYUTPING_LETTER_KINDS.has(s.kind) || PHONEME_ANCHOR_KINDS.has(s.kind),
  );
}

/**
 * Complete width-digit code for SQL IN variants — from ctx/prefix, pure digit mask, or dense code_digit slots.
 * Partial codes (not every position) return null so phoneme path can take unlimited bucket.
 */
export function narrowingCodeFromSpec(spec: MatchSpec, ctxCode?: string | null): string | null {
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
  spec: MatchSpec,
  ctx: Pick<ExecuteMatchSpecContext, 'db' | 'mode' | 'code' | 'shouldCancel'>,
): Promise<WordRow[]> {
  if (!spec || spec.width === 0) {
    return [];
  }
  throwIfSearchCancelled(ctx.shouldCancel);
  if (getEqualsSpan(spec) || spec.compound_kind) {
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
      [candidates] = await getCandidatesForLength(ctx.db, spec.width, {
        code,
        mode: ctx.mode,
        unlimited:
          specNeedsFullLengthBucket(spec)
          || Boolean(spec.extra?.workbench_full_bucket_scan)
          || Boolean(code)
          || Boolean(codePositions?.length),
        codePositions,
      });
    }
  }
  if (fromPhonemeIndex) {
    if (!spec.extra) spec.extra = {};
    spec.extra.phoneme_index_prefiltered = true;
  }
  throwIfSearchCancelled(ctx.shouldCancel);
  return applyMatchSpec(spec, candidates, ctx.db, ctx.mode, ctx.shouldCancel);
}

/** Filter + sort + page; `total` is the full sorted pool size (ADR-0064). */
export async function executeMatchSpecPage(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<{ rows: WordRow[]; total: number }> {
  if (!spec || spec.width === 0) {
    return { rows: [], total: 0 };
  }
  if (spec.extra?.dual_phoneme) {
    // Dual path materializes a truncated union; count that union after paging window math.
    const unpagedLimit = Math.max(ctx.limit + ctx.offset, ctx.limit) + 500;
    const base = {
      db: ctx.db,
      mode: ctx.mode,
      code: ctx.code ?? null,
      shouldCancel: ctx.shouldCancel,
    };
    const initialSpec = spec.extra?.dual_initial_spec as MatchSpec;
    const finalSpec = spec.extra?.dual_final_spec as MatchSpec;
    if (!initialSpec || !finalSpec) return { rows: [], total: 0 };
    const initialRows = sortWordRows(await filterMatchSpecRows(initialSpec, base)).slice(0, unpagedLimit);
    throwIfSearchCancelled(ctx.shouldCancel);
    const finalRows = sortWordRows(await filterMatchSpecRows(finalSpec, base)).slice(0, unpagedLimit);
    const tagged: WordRow[] = [
      ...initialRows.map((row) => ({ ...row, anchor_dimension: 'initial' })),
      ...finalRows.map((row) => ({ ...row, anchor_dimension: 'final' })),
    ];
    return {
      rows: tagged.slice(ctx.offset, ctx.offset + ctx.limit),
      total: tagged.length,
    };
  }
  const filtered = await filterMatchSpecRows(spec, ctx);
  throwIfSearchCancelled(ctx.shouldCancel);
  let sorted: WordRow[];
  const literalPositions = spec.extra?.literal_positions;
  if (spec.literal_priority && Array.isArray(literalPositions) && literalPositions.length) {
    const positions = literalPositions as Array<[number, string]>;
    sorted = [...filtered].sort((a, b) => literalPriorityCompare(a, b, positions));
  } else {
    sorted = sortWordRows(filtered);
  }
  return {
    rows: sorted.slice(ctx.offset, ctx.offset + ctx.limit),
    total: sorted.length,
  };
}

/** Port of run_position_query_tracked — filter, sort, then page. */
export async function executeMatchSpec(
  spec: MatchSpec,
  ctx: ExecuteMatchSpecContext,
): Promise<WordRow[]> {
  return (await executeMatchSpecPage(spec, ctx)).rows;
}
