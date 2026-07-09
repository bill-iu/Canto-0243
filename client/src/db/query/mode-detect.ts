/**
 * Pure 搜尋模式轉接 detect (介面轉接 / early UI).
 * FILLWORD alphabet inlined from contracts/fillword-connectives.json
 * (python scripts/codegen_fillword_connectives.py).
 * Codegen mjs: python scripts/codegen_query_mode_detect.py
 * Do not hand-edit frontend/query-mode-detect.mjs.
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

export function normalizeQuerySyntax(q: string): string {
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
export function isRelationSyntaxQuery(q: string): boolean {
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

export function isPingZeSerialQuery(q: string): boolean {
  const n = String(q || '').trim();
  if (!n || !PING_ZE_HAS_PZ.test(n)) return false;
  return PING_ZE_SLOT_RE.test(n);
}
