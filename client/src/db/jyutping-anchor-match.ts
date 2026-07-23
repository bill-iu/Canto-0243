/**
 * Jyutping anchor matching — port of app/services/jyutping_anchor_match.py
 */
import { isStandaloneNasalSyllableToken, syllableLetters } from './jyutping-codec.ts';
import {
  createMatchSpec,
  type MatchSpec,
  type SlotConstraint,
} from './position-match/spec.ts';
import type { JyutpingAnchorQuery, ParsedQuery } from './query-types.ts';
import { QueryKind } from './query-kind.ts';
import { decodePhonemeField } from './phoneme-codec.ts';
import { matchesRhymeLettersAtPosition } from './rime-index.ts';
import type { AnchorKind } from './jyutping-anchor-parse.ts';

export function parseSyllableLetterTokens(jyutping: string): string[] {
  return jyutping
    .trim()
    .split(/\s+/)
    .map((s) => syllableLetters(s));
}

function matchesSyllableLettersAtPosition(
  word: { jyutping?: unknown },
  pos: number,
  letters: string,
): boolean {
  const syls = parseSyllableLetterTokens(String(word.jyutping ?? ''));
  return pos < syls.length && syls[pos] === letters.toLowerCase();
}

function matchesInitialLettersAtPosition(
  word: { jyutping?: unknown; initials?: unknown },
  pos: number,
  letter: string,
): boolean {
  const jyut = String(word.jyutping ?? '');
  const tokens = jyut.trim().split(/\s+/);
  if (pos < tokens.length && isStandaloneNasalSyllableToken(tokens[pos]!)) {
    return false;
  }
  const parts = decodePhonemeField(word.initials, 'initial');
  return pos < parts.length && parts[pos] === letter.toLowerCase();
}

export function matchesJyutpingAnchorAtPosition(
  word: { jyutping?: unknown; initials?: unknown; finals?: unknown },
  pos: number,
  kind: AnchorKind,
  value: string,
): boolean {
  const letters = value.toLowerCase();
  if (kind === 'syllable_letters') {
    return matchesSyllableLettersAtPosition(word, pos, letters);
  }
  if (kind === 'initial_letters') {
    return matchesInitialLettersAtPosition(word, pos, letters);
  }
  if (kind === 'rhyme_letters') {
    return matchesRhymeLettersAtPosition(word, pos, letters);
  }
  return false;
}

function slots(spec: MatchSpec): SlotConstraint[] {
  if (!spec.slots) {
    spec.slots = [];
  }
  return spec.slots;
}

function applyJyutpingAnchorCodeSlots(spec: MatchSpec, parsed: JyutpingAnchorQuery): void {
  if (parsed.code_slots?.length) {
    for (const [pos, digit] of parsed.code_slots) {
      slots(spec).push({ pos, kind: 'code_digit', value: digit });
    }
  } else if (parsed.code_prefix && parsed.width === parsed.code_prefix.length) {
    for (let i = 0; i < parsed.code_prefix.length; i++) {
      slots(spec).push({ pos: i, kind: 'code_digit', value: parsed.code_prefix[i]! });
    }
  }
}

/** Port of jyutping_anchor_match.build_jyutping_dual_match_specs */
export function buildJyutpingDualMatchSpecs(
  parsed: JyutpingAnchorQuery,
): [MatchSpec, MatchSpec] {
  const base = (): MatchSpec => {
    const spec = createMatchSpec(parsed.width);
    spec.mask = '?'.repeat(parsed.width);
    applyJyutpingAnchorCodeSlots(spec, parsed);
    return spec;
  };

  const initial = base();
  slots(initial).push({
    pos: parsed.anchor_pos,
    kind: 'initial_letters',
    value: parsed.dual_initial_value || parsed.anchor_value,
  });

  const final = base();
  slots(final).push({
    pos: parsed.anchor_pos,
    kind: 'rhyme_letters',
    value: parsed.anchor_value,
  });

  return [initial, final];
}

/** Port of jyutping_anchor_match.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind !== QueryKind.JYUTPING_ANCHOR) {
    return null;
  }
  const q = parsed as JyutpingAnchorQuery;
  if (q.dual_phoneme) {
    const [initial, final] = buildJyutpingDualMatchSpecs(q);
    const carrier = createMatchSpec(q.width);
    applyJyutpingAnchorCodeSlots(carrier, q);
    if (!carrier.extra) {
      carrier.extra = {};
    }
    carrier.extra.dual_phoneme = true;
    carrier.extra.dual_initial_spec = initial;
    carrier.extra.dual_final_spec = final;
    return carrier;
  }
  const spec = createMatchSpec(q.width);
  spec.mask = '?'.repeat(q.width);
  slots(spec).push({
    pos: q.anchor_pos,
    kind: q.anchor_kind as AnchorKind,
    value: q.anchor_value,
  });
  applyJyutpingAnchorCodeSlots(spec, q);
  return spec;
}
