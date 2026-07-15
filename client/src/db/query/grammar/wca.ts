/** Port of query_grammar/wca. */
import {
  createMatchSpec,
  type ConstraintKind,
  type MatchSpec,
} from '../../position-match/spec.ts';
import { QueryKind } from '../../query-kind.ts';
import type { ParsedQuery, WildcardCodeAnchorQuery } from '../../query-types.ts';
import { isWildcardChar } from './mask.ts';
import { CODE_TAIL_MIDDLE, GRAMMAR_PLUS } from './shared.ts';

function wcaTokenize(body: string): Array<[string, string]> | null {
  const tokens: Array<[string, string]> = [];
  let i = 0;
  while (i < body.length) {
    const ch = body[i]!;
    if (isWildcardChar(ch)) {
      tokens.push(['wild', ch]);
      i += 1;
    } else if (ch === GRAMMAR_PLUS || ch === CODE_TAIL_MIDDLE) {
      tokens.push(['star', '']);
      i += 1;
    } else if (/\d/.test(ch)) {
      while (i < body.length && /\d/.test(body[i]!)) {
        tokens.push(['code', body[i]!]);
        i += 1;
      }
    } else if (/[\u4e00-\u9fff]/.test(ch)) {
      tokens.push(['ref', ch]);
      i += 1;
    } else {
      return null;
    }
  }
  return tokens.length ? tokens : null;
}

function wcaTokensToSpec(
  tokens: Array<[string, string]>,
  headLiteral?: string,
): Omit<WildcardCodeAnchorQuery, 'kind' | 'raw_q'> | null {
  const syllables: Array<Record<string, string | boolean>> = [];
  if (headLiteral) {
    syllables.push({ literal: headLiteral });
  }
  let i = 0;
  while (i < tokens.length) {
    const [kind, val] = tokens[i]!;
    if (kind === 'wild') {
      syllables.push({ wild: true });
      i += 1;
    } else if (kind === 'code') {
      syllables.push({ code: val });
      i += 1;
    } else if (kind === 'star') {
      if (i + 1 < tokens.length && tokens[i + 1]![0] === 'ref') {
        syllables.push({ ref: tokens[i + 1]![1], star_before: true });
        i += 2;
      } else {
        syllables.push({ wild: true });
        i += 1;
      }
    } else if (kind === 'ref') {
      const last = syllables[syllables.length - 1];
      if (last && 'code' in last && !('ref' in last)) {
        last.ref = val;
        i += 1;
      } else {
        return null;
      }
    } else {
      return null;
    }
  }
  if (!syllables.length) {
    return null;
  }
  if (!syllables.some((s) => 'code' in s) || !syllables.some((s) => 'ref' in s)) {
    return null;
  }
  if (!headLiteral && !(tokens[0] && tokens[0][0] === 'wild')) {
    return null;
  }
  const slots: WildcardCodeAnchorQuery['slots'] = [];
  for (let pos = 0; pos < syllables.length; pos++) {
    const syl = syllables[pos]!;
    if ('literal' in syl) {
      slots.push({ pos, kind: 'literal_char', value: String(syl.literal) });
    }
    if ('code' in syl) {
      slots.push({ pos, kind: 'code_digit', value: String(syl.code) });
    }
    if ('ref' in syl) {
      slots.push({ pos, kind: 'final_anchor', value: String(syl.ref) });
    }
  }
  return { width: syllables.length, slots, head_literal: headLiteral };
}

/** Port of wca.parse_wildcard_code_anchor_query */
export function parseWildcardCodeAnchorQuery(q: string): WildcardCodeAnchorQuery | null {
  if (!q || q.includes('@') || q.includes('=')) {
    return null;
  }
  if (/^\d+\+/.test(q)) {
    return null;
  }
  let m = q.match(/^\+([\u4e00-\u9fff])([?_%0-9+\u4e00-\u9fff]+)$/);
  if (m) {
    const tokens = wcaTokenize(m[2]!);
    if (!tokens) {
      return null;
    }
    const spec = wcaTokensToSpec(tokens, m[1]);
    if (!spec) {
      return null;
    }
    return { kind: QueryKind.WILDCARD_CODE_ANCHOR, raw_q: q, ...spec };
  }
  if (!'?_%'.includes(q[0]!)) {
    return null;
  }
  const tokens = wcaTokenize(q);
  if (!tokens) {
    return null;
  }
  const spec = wcaTokensToSpec(tokens);
  if (!spec) {
    return null;
  }
  return { kind: QueryKind.WILDCARD_CODE_ANCHOR, raw_q: q, ...spec };
}

/** Port of query_grammar.wca.to_match_spec */
export function toMatchSpec(parsed: ParsedQuery): MatchSpec | null {
  if (parsed.kind !== QueryKind.WILDCARD_CODE_ANCHOR) {
    return null;
  }
  const q = parsed as WildcardCodeAnchorQuery;
  const spec = createMatchSpec(q.width);
  spec.mask = '?'.repeat(q.width);
  if (!spec.slots) {
    spec.slots = [];
  }
  for (const slot of q.slots) {
    const kind = slot.kind as ConstraintKind;
    spec.slots.push({ pos: slot.pos, kind, value: slot.value });
    if (kind === 'literal_char' && slot.value) {
      spec.mask = spec.mask.slice(0, slot.pos) + slot.value + spec.mask.slice(slot.pos + 1);
    }
  }
  return spec;
}
