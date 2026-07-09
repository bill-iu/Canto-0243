/**
 * AUTO-GENERATED from client/src/db/query/mode-detect.ts — do not edit.
 * Run: python scripts/codegen_query_mode_detect.py
 */

const FILLWORD_CONNECTIVES = '與和或共同及跟而且並向';
const COMPOUND_CONNECT_SYN_RE = new RegExp(
  `^(\\d*)~([${FILLWORD_CONNECTIVES}])~([\\u4e00-\\u9fff])?$`,
);
const COMPOUND_CONNECT_ANT_RE = new RegExp(
  `^(\\d*)!([${FILLWORD_CONNECTIVES}])!([\\u4e00-\\u9fff])?$`,
);
const COMPOUND_SYN_RE = /^(\d*)~~([\u4e00-\u9fff])?$/;
const COMPOUND_ANT_RE = /^(\d*)!!([\u4e00-\u9fff])?$/;
const RELATION_LOOKUP_RE = /^(\d*)([~!])([\u4e00-\u9fff]+)$/;

const PING_ZE_SLOT_RE = /^[PZ0-9]+$/i;
const PING_ZE_HAS_PZ = /[PZ]/i;

export function normalizeQuerySyntax(q) {
  return String(q || '')
    .replace(/＊/g, '*')
    .replace(/﹡/g, '*')
    .replace(/！！/g, '!!')
    .replace(/～～/g, '~~')
    .replace(/！/g, '!')
    .replace(/～/g, '~')
    .replace(/？/g, '?');
}

/** Pure regex detect — Portable 介面轉接 + PWA early detect. */
export function isRelationSyntaxQuery(q) {
  const n = normalizeQuerySyntax(String(q || '').trim());
  if (!n) return false;
  return (
    COMPOUND_CONNECT_SYN_RE.test(n) ||
    COMPOUND_CONNECT_ANT_RE.test(n) ||
    COMPOUND_SYN_RE.test(n) ||
    COMPOUND_ANT_RE.test(n) ||
    RELATION_LOOKUP_RE.test(n)
  );
}

export function isPingZeSerialQuery(q) {
  const n = String(q || '').trim();
  if (!n || !PING_ZE_HAS_PZ.test(n)) return false;
  return PING_ZE_SLOT_RE.test(n);
}
