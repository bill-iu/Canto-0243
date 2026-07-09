/**
 * Pure 搜尋模式轉接 detect (介面轉接) — Arch Phase B PR3.
 * Keep behaviour aligned with client/src/db/query/parse.ts isRelationSyntaxQuery
 * and client/src/db/ping-zak.ts isPingZeSerialQuery (parity tests).
 */

const FILLWORD_CONNECTIVES = "與和或共同及跟而且並向";

const COMPOUND_CONNECT_SYN_RE = new RegExp(
  `^(\\d*)~([${FILLWORD_CONNECTIVES}])~([\\u4e00-\\u9fff])?$`
);
const COMPOUND_CONNECT_ANT_RE = new RegExp(
  `^(\\d*)!([${FILLWORD_CONNECTIVES}])!([\\u4e00-\\u9fff])?$`
);
const COMPOUND_SYN_RE = /^(\d*)~~([\u4e00-\u9fff])?$/;
const COMPOUND_ANT_RE = /^(\d*)!!([\u4e00-\u9fff])?$/;
const RELATION_LOOKUP_RE = /^(\d*)([~!])([\u4e00-\u9fff]+)$/;

const PING_ZE_SLOT_RE = /^[PZ0-9]+$/i;
const PING_ZE_HAS_PZ = /[PZ]/i;

export function normalizeQuerySyntax(q) {
  return String(q || "")
    .replace(/＊/g, "*")
    .replace(/﹡/g, "*")
    .replace(/！！/g, "!!")
    .replace(/～～/g, "~~")
    .replace(/！/g, "!")
    .replace(/～/g, "~")
    .replace(/？/g, "?");
}

export function isRelationSyntaxQuery(q) {
  const n = normalizeQuerySyntax(String(q || "").trim());
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
  const n = String(q || "").trim();
  if (!n || !PING_ZE_HAS_PZ.test(n)) return false;
  return PING_ZE_SLOT_RE.test(n);
}
