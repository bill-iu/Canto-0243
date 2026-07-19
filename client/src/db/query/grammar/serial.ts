/** Port of query_grammar/serial. */
import { QueryKind } from '../../query-kind.ts';
import type {
  ParsedQuery,
  PrefixWildcardEqualsQuery,
  SerialPhonemeAnchorQuery,
} from '../../query-types.ts';
import {
  attachEqualsSpan,
  createMatchSpec,
  getEqualsSpan,
  type MatchSpec,
} from '../../position-match/spec.ts';
import { buildEqualsMatchSpec, isFramedEqualsQuery } from './equals.ts';
import { CODE_TAIL_MIDDLE } from './shared.ts';

/** Port of query_grammar/serial.parse_prefix_wildcard_equals_query */
export function parsePrefixWildcardEqualsQuery(q: string): PrefixWildcardEqualsQuery | null {
  const m = q.match(/^\?([\u4e00-\u9fff]{2,})=$/);
  if (!m) {
    return null;
  }
  const ref = m[1]!;
  return {
    kind: QueryKind.PREFIX_WILDCARD_EQUALS,
    raw_q: q,
    inner_q: `${ref}=`,
    ref_literal: ref,
    width: ref.length + 1,
  };
}

/** Port of query_grammar/serial.parse_prefix_wildcard_initial_query */
export function parsePrefixWildcardInitialQuery(q: string): PrefixWildcardEqualsQuery | null {
  const m = q.match(/^\?[\^=]([\u4e00-\u9fff]{2,})$/);
  if (!m) {
    return null;
  }
  const ref = m[1]!;
  return {
    kind: QueryKind.PREFIX_WILDCARD_EQUALS,
    raw_q: q,
    inner_q: `^${ref}`,
    ref_literal: ref,
    width: ref.length + 1,
  };
}

const PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT =
  '前綴通配等號查詢須以 `=` 結尾。例：`?困潦倒=`（唔好漏尾格 `=`）。';
const PURE_CHARS_SERIAL_HINT =
  '每個 `{字}=`／`^{字}` 前須有 0243 碼。例：`04困=49倒=`（唔好寫 `窮困=潦倒=`）。';
const INITIAL_RHYME_DUAL_MARK_HINT =
  '唔好同時用 `^`（同聲）同尾 `=`（同韻）。例：`^香` 或 `香=`（唔好寫 `^香=`）。';

/** Port of serial.prefix_wildcard_equals_missing_eq_hint */
export function prefixWildcardEqualsMissingEqHint(q: string): string | null {
  if (/^\?[\u4e00-\u9fff]{3,}$/.test(q)) {
    return PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT;
  }
  return null;
}

/** Port of serial.parse_pure_chars_serial_hint */
export function parsePureCharsSerialHint(q: string): string | null {
  if (!q || !/^[\u4e00-\u9fff=^]+$/.test(q)) {
    return null;
  }
  if (/^[\u4e00-\u9fff]=$/.test(q) || /^\^[\u4e00-\u9fff]+$/.test(q)) {
    return null;
  }
  if (isFramedEqualsQuery(q)) {
    return null;
  }
  if (/(?<![0-9])([\u4e00-\u9fff])=/.test(q)) {
    return PURE_CHARS_SERIAL_HINT;
  }
  return null;
}

/** Port of serial.initial_rhyme_dual_mark_hint (ADR-0062) */
export function initialRhymeDualMarkHint(q: string): string | null {
  if (/\^[\u4e00-\u9fff]+=/.test(q) || /\^[\u4e00-\u9fff]=/.test(q)) {
    return INITIAL_RHYME_DUAL_MARK_HINT;
  }
  if (/\d[\u4e00-\u9fff]=/.test(q) && /\d\^[\u4e00-\u9fff]/.test(q)) {
    return INITIAL_RHYME_DUAL_MARK_HINT;
  }
  return null;
}

const SERIAL_CHARSET_RE = /^[0-9?=^\u4e00-\u9fff]+$/;

function framedEqualsBlocksSerial(q: string): boolean {
  if (!isFramedEqualsQuery(q)) {
    return false;
  }
  const m = q.match(/^(\d*)(\^|=)?([\u4e00-\u9fff]+)(=)?(\d*)$/);
  if (!m) {
    return false;
  }
  if (m[2]) {
    return true;
  }
  if (m[5]) {
    return true;
  }
  if (m[4] && (m[3]?.length ?? 0) >= 2) {
    return true;
  }
  if (m[4] && m[1] && !m[5]) {
    return true;
  }
  return false;
}

function scanSerialPhoneme(
  q: string,
  constraint: 'final' | 'initial',
): Omit<SerialPhonemeAnchorQuery, 'kind' | 'raw_q'> | null {
  let i = 0;
  let pos = 0;
  const code_slots: Array<[number, string]> = [];
  const anchors: Array<[number, string]> = [];
  const maskChars: string[] = [];

  while (i < q.length) {
    const ch = q[i]!;
    if (ch === '?') {
      maskChars.push('?');
      pos += 1;
      i += 1;
      continue;
    }
    if (/\d/.test(ch)) {
      const anchorRe =
        constraint === 'final'
          ? /^(\d)([\u4e00-\u9fff])=(?=[0-9?^=]|$)/
          : /^(\d)[\^=]([\u4e00-\u9fff])(?=[0-9?^=]|$)/;
      const m = q.slice(i).match(anchorRe);
      if (m) {
        code_slots.push([pos, m[1]!]);
        anchors.push([pos, m[2]!]);
        maskChars.push(m[1]!);
        pos += 1;
        i += m[0].length;
        continue;
      }
      code_slots.push([pos, ch]);
      maskChars.push(ch);
      pos += 1;
      i += 1;
      continue;
    }
    return null;
  }
  if (!anchors.length) {
    return null;
  }
  return {
    width: pos,
    constraint,
    code_slots,
    anchors,
    mask: maskChars.join(''),
  };
}

/** Port of serial.parse_serial_phoneme_anchor_query */
export function parseSerialPhonemeAnchorQuery(q: string): SerialPhonemeAnchorQuery | null {
  if (!q || !SERIAL_CHARSET_RE.test(q)) {
    return null;
  }
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes('+') || q.includes('@') || q.includes('*') || q.includes('_') || q.includes('%')) {
    return null;
  }
  if (framedEqualsBlocksSerial(q)) {
    return null;
  }
  if (/^[\u4e00-\u9fff]=$/.test(q)) {
    return null;
  }
  const hasRhyme = /\d[\u4e00-\u9fff]=/.test(q);
  const hasInitial = /\d[\^=][\u4e00-\u9fff]/.test(q);
  if (hasRhyme && hasInitial) {
    return null;
  }
  const constraint: 'final' | 'initial' = hasRhyme ? 'final' : 'initial';
  if (!hasRhyme && !hasInitial) {
    return null;
  }
  const parsed = scanSerialPhoneme(q, constraint);
  if (!parsed) {
    return null;
  }
  return { kind: QueryKind.SERIAL_PHONEME, raw_q: q, ...parsed };
}

/** Port of query_grammar.serial.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind === QueryKind.PREFIX_WILDCARD_EQUALS) {
    const q = parsed as PrefixWildcardEqualsQuery;
    const spec = buildEqualsMatchSpec(q.inner_q);
    if (!spec) {
      return createMatchSpec(0);
    }
    spec.width = q.width;
    const span = getEqualsSpan(spec);
    if (span) {
      attachEqualsSpan(spec, {
        ref_literal: span.ref_literal,
        start_pos: 1,
        dimension: span.dimension,
        phoneme_anchor_only: true,
        whole_word: false,
      });
    }
    spec.mask = '?'.repeat(q.width);
    if (!spec.extra) {
      spec.extra = {};
    }
    spec.extra.prefix_wildcard_equals = true;
    return spec;
  }
  if (parsed.kind === QueryKind.SERIAL_PHONEME) {
    const q = parsed as SerialPhonemeAnchorQuery;
    const spec = createMatchSpec(q.width);
    spec.mask = q.mask.length === q.width ? q.mask : '?'.repeat(q.width);
    if (!spec.slots) {
      spec.slots = [];
    }
    for (const [pos, digit] of q.code_slots) {
      spec.slots.push({ pos, kind: 'code_digit', value: digit });
    }
    const kind = q.constraint === 'final' ? 'final_anchor' : 'initial_anchor';
    for (const [pos, anchor] of q.anchors) {
      spec.slots.push({ pos, kind, value: anchor });
    }
    return spec;
  }
  return null;
}
