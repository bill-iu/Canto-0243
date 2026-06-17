/** ponytail: keep in sync with query_parse.is_relation_syntax_query */
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

export function normalizeQuerySyntax(q) {
  return q
    .replace(/＊/g, "*")
    .replace(/﹡/g, "*")
    .replace(/！！/g, "!!")
    .replace(/～～/g, "~~")
    .replace(/！/g, "!")
    .replace(/～/g, "~")
    .replace(/？/g, "?");
}

export function isRelationSyntaxQuery(q) {
  const n = normalizeQuerySyntax((q || "").trim());
  if (!n) return false;
  return (
    COMPOUND_CONNECT_SYN_RE.test(n) ||
    COMPOUND_CONNECT_ANT_RE.test(n) ||
    COMPOUND_SYN_RE.test(n) ||
    COMPOUND_ANT_RE.test(n) ||
    RELATION_LOOKUP_RE.test(n)
  );
}

export function modeRedirectHint(mode) {
  const label = mode === "m2" ? "02493模式（緊）" : "0243模式（鬆）";
  return `此語法已切換至 ${label} 查詢`;
}
