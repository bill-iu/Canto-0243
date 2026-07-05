var __defProp = Object.defineProperty;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __esm = (fn, res, err) => function __init() {
  if (err) throw err[0];
  try {
    return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
  } catch (e) {
    throw err = [e], e;
  }
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};

// src/db/init.ts
var init_exports = {};
__export(init_exports, {
  db: () => db,
  getDatabase: () => getDatabase,
  getDefaultDbUrl: () => getDefaultDbUrl,
  initializeDatabase: () => initializeDatabase,
  isDatabaseInitialized: () => isDatabaseInitialized,
  resetDatabase: () => resetDatabase
});
import initSqlJs from "sql.js";
function defaultDbUrl() {
  const ver = import.meta.env?.VITE_LEXICON_VERSION || "dev";
  return new URL(`lyrics.${ver}.db`, import.meta.env.BASE_URL).toString();
}
function getDefaultDbUrl() {
  return defaultDbUrl();
}
async function initializeDatabase(dbPath2 = defaultDbUrl()) {
  if (db && isInitialized) {
    return db;
  }
  try {
    const SQL2 = await initSqlJs({
      locateFile: (file) => {
        if (file.endsWith(".wasm")) {
          return `https://sql.js.org/dist/${file}`;
        }
        return file;
      }
    });
    const response = await fetch(dbPath2);
    if (!response.ok) {
      throw new Error(`Failed to fetch lexicon package (${response.status})`);
    }
    const arrayBuffer = await response.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    db = new SQL2.Database(uint8Array);
    isInitialized = true;
    console.log("Database initialized successfully");
    return db;
  } catch (error) {
    console.error("Failed to initialize database:", error);
    throw new Error("Could not initialize database. Please ensure the lexicon package is accessible.");
  }
}
function getDatabase() {
  if (!db) {
    throw new Error("Database not initialized. Call initializeDatabase() first.");
  }
  return db;
}
function isDatabaseInitialized() {
  return isInitialized;
}
function resetDatabase() {
  if (db) {
    db.close();
    db = null;
    isInitialized = false;
  }
}
var db, isInitialized;
var init_init = __esm({
  "src/db/init.ts"() {
    db = null;
    isInitialized = false;
  }
});

// src/db/query-engine.ts
var query_engine_exports = {};
__export(query_engine_exports, {
  CODE_TAIL_MIDDLE: () => CODE_TAIL_MIDDLE,
  QueryEngine: () => QueryEngine,
  QueryKind: () => QueryKind,
  RouteKind: () => RouteKind,
  buildEqualsMatchSpec: () => buildEqualsMatchSpec,
  codePrefixedWholeWordEqualsEmptyHint: () => codePrefixedWholeWordEqualsEmptyHint,
  executeSearch: () => executeSearch,
  hybridQueryFromTailEquals: () => hybridQueryFromTailEquals,
  isFramedEqualsQuery: () => isFramedEqualsQuery,
  isHybridTailEqualsAlias: () => isHybridTailEqualsAlias,
  normalizeAndParse: () => normalizeAndParse,
  normalizeQuery: () => normalizeQuery,
  parseQuery: () => parseQuery,
  queryEngine: () => queryEngine,
  searchWords: () => searchWords
});
function routeKindFor(kind) {
  return QUERY_KIND_META[kind]?.route || "empty" /* EMPTY */;
}
function normalizeQuery(q) {
  if (!q) return q;
  let normalized = q.trim();
  const fullToHalf = {
    "\uFF01": "!",
    "\uFF20": "@",
    "\uFF03": "#",
    "\uFF04": "$",
    "\uFF05": "%",
    "\uFF06": "&",
    "\uFF0A": "*",
    "\uFF08": "(",
    "\uFF09": ")",
    "\uFF0B": "+",
    "\uFF0D": "-",
    "\uFF1D": "=",
    "\uFF17": "7",
    "\uFF18": "8",
    "\uFF1F": "?",
    "\u3001": ",",
    "\u3002": "."
  };
  normalized = normalized.replace(/[！＠＃＄％＆＊（）＋－＝７８？、。]/g, (match) => fullToHalf[match] || match);
  return normalized;
}
function isPureDigits(q) {
  return /^\d+$/.test(q);
}
function hasChineseChars(q) {
  return /[\u4e00-\u9fff]/.test(q);
}
function hasJyutpingChars(q) {
  return /[a-zA-Z]/.test(q);
}
function parseQuery(q) {
  const normalized = normalizeQuery(q);
  if (normalized.startsWith("~") || normalized.startsWith("\uFF01") || normalized.startsWith("!") || normalized.startsWith("\uFF5E")) {
    return {
      kind: "relation_lookup" /* RELATION_LOOKUP */,
      raw_q: normalized,
      relation_kind: normalized.startsWith("~") || normalized.startsWith("\uFF5E") ? "syn" : "ant",
      word: normalized.slice(1)
    };
  }
  if (isHybridTailEqualsAlias(normalized)) {
    return {
      kind: "hybrid_tail_equals_alias" /* HYBRID_TAIL_EQUALS_ALIAS */,
      raw_q: normalized,
      hybrid_q: hybridQueryFromTailEquals(normalized)
    };
  }
  if (isFramedEqualsQuery(normalized)) {
    return { kind: "equals" /* EQUALS */, raw_q: normalized };
  }
  if (looksLikeMaskQuery(normalized)) {
    return { kind: "mask" /* MASK */, raw_q: normalized };
  }
  if (isPureDigits(normalized)) {
    return { kind: "digit_code" /* DIGIT_CODE */, raw_q: normalized };
  }
  if (hasChineseChars(normalized)) {
    return { kind: "word_lookup" /* WORD_LOOKUP */, raw_q: normalized };
  }
  if (hasJyutpingChars(normalized)) {
    return { kind: "jyutping_fragment" /* JYUTPING_FRAGMENT */, raw_q: normalized };
  }
  return { kind: "unmatched" /* UNMATCHED */, raw_q: normalized, hint: "\u7121\u6CD5\u8FA8\u8A8D\u7684\u67E5\u8A62\u8A9E\u6CD5" };
}
function normalizeAndParse(q) {
  return parseQuery(normalizeQuery(q));
}
function looksLikeMaskQuery(q) {
  return /[?*_%]/.test(q);
}
function isHybridTailEqualsAlias(q) {
  return HYBRID_TAIL_EQUALS_RE.test(q);
}
function hybridQueryFromTailEquals(q) {
  return q.slice(0, -1);
}
function isFramedEqualsQuery(q) {
  if (q.includes(CODE_TAIL_MIDDLE) || q.includes("@") || isHybridTailEqualsAlias(q)) {
    return false;
  }
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)(=)?(\d*)$/);
  if (!match) {
    return false;
  }
  const target = match[3] || "";
  if (!target) {
    return false;
  }
  const left_code = match[1] || "";
  const right_code = match[5] || "";
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  if (right_equal && target.length >= 2) {
    return true;
  }
  if (right_equal && left_code && target.length === 1) {
    return true;
  }
  if (inner_equal && left_code && right_code) {
    return true;
  }
  if (inner_equal && left_code && !right_equal) {
    return true;
  }
  if (inner_equal && !left_code && !right_equal && target.length >= 2) {
    return true;
  }
  return false;
}
function buildEqualsMatchSpec(q) {
  const match = q.match(/^(\d*)(=)?([\u4e00-\u9fff]+)?(=)?(\d*)$/);
  if (!match) {
    return null;
  }
  const target_str = match[3] || "";
  if (!target_str) {
    return null;
  }
  const left_code = match[1] || "";
  const right_code = match[5] || "";
  const right_equal = Boolean(match[4]);
  const inner_equal = Boolean(match[2]);
  const target_length = target_str.length;
  const expected_length = left_code.length + right_code.length || target_length;
  const start_pos = Math.max(0, left_code.length - target_length);
  const full_code = left_code + right_code;
  const span = {
    ref_literal: target_str,
    start_pos,
    dimension: right_equal ? "final" : "initial",
    phoneme_anchor_only: Boolean(left_code && (right_code || inner_equal)),
    whole_word: start_pos === 0 && target_length === expected_length
  };
  return {
    width: expected_length,
    code_prefix: full_code || void 0,
    equals_span: span
  };
}
async function codePrefixedWholeWordEqualsEmptyHint(spec, db3) {
  const span = spec.equals_span;
  if (!span || !span.whole_word) {
    return null;
  }
  const code = spec.code_prefix || "";
  const literal = span.ref_literal;
  if (!code || code.length !== literal.length) {
    return null;
  }
  const sql = "SELECT COUNT(*) as count FROM words WHERE char = ?";
  const stmt = db3.prepare(sql);
  stmt.bind([literal]);
  const result = stmt.step() ? stmt.getAsObject() : { count: 0 };
  stmt.free();
  if (result.count === 0) {
    return null;
  }
  return CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT.replace("{literal}", literal).replace("{code}", code);
}
async function executeSearch(ctx) {
  if (!isDatabaseInitialized()) {
    await initializeDatabase();
  }
  const db3 = getDatabase();
  if (!ctx.q) {
    return executeListFilter(db3, ctx);
  }
  const parsed = normalizeAndParse(ctx.q);
  return await dispatch(parsed, { ...ctx, db: db3 });
}
function executeListFilter(db3, ctx) {
  const sql = `SELECT word, jyutping, code FROM words ORDER BY word LIMIT ? OFFSET ?`;
  const stmt = db3.prepare(sql);
  const results = [];
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0
    });
  }
  stmt.free();
  return { items: results };
}
async function dispatch(parsed, ctx) {
  const routeKind = routeKindFor(parsed.kind);
  const { db: db3, mode, limit, offset } = ctx;
  switch (routeKind) {
    case "digit" /* DIGIT */:
      if (parsed.kind === "digit_code" /* DIGIT_CODE */) {
        return executeDigitCodeQuery(parsed, db3, mode, limit, offset);
      }
      break;
    case "lookup" /* LOOKUP */:
      if (parsed.kind === "word_lookup" /* WORD_LOOKUP */) {
        return executeWordLookup(parsed, db3, mode, limit, offset);
      }
      if (parsed.kind === "jyutping_fragment" /* JYUTPING_FRAGMENT */) {
        return executeJyutpingFragment(parsed, db3, limit, offset);
      }
      break;
    case "mask_family" /* MASK_FAMILY */:
      if (parsed.kind === "equals" /* EQUALS */) {
        return executeEqualsQuery(parsed, db3, mode, limit, offset);
      }
      if (parsed.kind === "hybrid_tail_equals_alias" /* HYBRID_TAIL_EQUALS_ALIAS */) {
        return executeMaskFamily(
          { kind: "mask" /* MASK */, raw_q: parsed.hybrid_q },
          db3,
          mode,
          limit,
          offset
        );
      }
      return executeMaskFamily(parsed, db3, mode, limit, offset);
    case "relation" /* RELATION */:
      if (parsed.kind === "relation_lookup" /* RELATION_LOOKUP */) {
        return executeRelationLookup(parsed, db3, mode, limit, offset);
      }
      break;
    case "unmatched" /* UNMATCHED */:
      if (parsed.kind === "unmatched" /* UNMATCHED */) {
        const unmatched = parsed;
        return { items: [], hint: unmatched.hint };
      }
      break;
  }
  return { items: [] };
}
function executeDigitCodeQuery(parsed, db3, mode, limit, offset) {
  const normalizedMode = mode === "m1" ? "0243" : mode === "m2" ? "02493" : mode;
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE code GLOB ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  const stmt = db3.prepare(sql);
  const results = [];
  const pattern = parsed.raw_q.replace(/\*/g, "%").replace(/\?/g, "_");
  stmt.bind([pattern, limit, offset]);
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0
    });
  }
  stmt.free();
  return { items: results };
}
function executeWordLookup(parsed, db3, mode, limit, offset) {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE word LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  const stmt = db3.prepare(sql);
  const results = [];
  stmt.bind([`%${parsed.raw_q}%`, limit, offset]);
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0
    });
  }
  stmt.free();
  return { items: results };
}
function executeJyutpingFragment(parsed, db3, limit, offset) {
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE jyutping LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  const stmt = db3.prepare(sql);
  const results = [];
  stmt.bind([`%${parsed.raw_q}%`, limit, offset]);
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0
    });
  }
  stmt.free();
  return { items: results };
}
async function executeEqualsQuery(parsed, db3, mode, limit, offset) {
  const spec = buildEqualsMatchSpec(parsed.raw_q);
  if (!spec) {
    return { items: [], hint: "\u7121\u6548\u7684\u7B49\u865F\u67E5\u8A62\u8A9E\u6CD5" };
  }
  const span = spec.equals_span;
  const { ref_literal, dimension, phoneme_anchor_only, whole_word } = span;
  const { code_prefix } = spec;
  if (whole_word && code_prefix) {
    const sql = `
      SELECT w.word, w.jyutping, w.code
      FROM words w
      WHERE w.char = ? AND w.code = ?
      ORDER BY w.word
      LIMIT ? OFFSET ?
    `;
    const stmt = db3.prepare(sql);
    stmt.bind([ref_literal, code_prefix, limit, offset]);
    const results = [];
    while (stmt.step()) {
      const row = stmt.getAsObject();
      results.push({
        word: row.word,
        jyutping: row.jyutping,
        code: row.code,
        score: 0
      });
    }
    stmt.free();
    if (results.length === 0) {
      const hint = await codePrefixedWholeWordEqualsEmptyHint(spec, db3);
      return { items: [], hint: hint || "\u672A\u627E\u5230\u7B26\u5408\u7684\u7D50\u679C" };
    }
    return { items: results };
  }
  if (code_prefix && ref_literal) {
    const codeLength = code_prefix.length;
    const expectedLength = spec.width;
    if (dimension === "final" || dimension === "rhyme") {
      const refSql = "SELECT jyutping, code FROM words WHERE char = ?";
      const refStmt = db3.prepare(refSql);
      refStmt.bind([ref_literal]);
      const refRow = refStmt.step() ? refStmt.getAsObject() : null;
      refStmt.free();
      if (refRow) {
        const pattern2 = code_prefix + "%";
        const sql2 = `
          SELECT word, jyutping, code
          FROM words
          WHERE code LIKE ? AND LENGTH(char) = ?
          ORDER BY word
          LIMIT ? OFFSET ?
        `;
        const stmt2 = db3.prepare(sql2);
        stmt2.bind([pattern2, expectedLength, limit, offset]);
        const results2 = [];
        while (stmt2.step()) {
          const row = stmt2.getAsObject();
          results2.push({
            word: row.word,
            jyutping: row.jyutping,
            code: row.code,
            score: 0
          });
        }
        stmt2.free();
        return { items: results2 };
      }
    }
    const pattern = code_prefix + "%";
    const sql = `
      SELECT word, jyutping, code
      FROM words
      WHERE code LIKE ? AND LENGTH(char) = ?
      ORDER BY word
      LIMIT ? OFFSET ?
    `;
    const stmt = db3.prepare(sql);
    stmt.bind([pattern, expectedLength, limit, offset]);
    const results = [];
    while (stmt.step()) {
      const row = stmt.getAsObject();
      results.push({
        word: row.word,
        jyutping: row.jyutping,
        code: row.code,
        score: 0
      });
    }
    stmt.free();
    return { items: results };
  }
  if (!code_prefix && ref_literal && dimension === "initial") {
    const refSql = "SELECT jyutping FROM words WHERE char = ?";
    const refStmt = db3.prepare(refSql);
    refStmt.bind([ref_literal]);
    const refRow = refStmt.step() ? refStmt.getAsObject() : null;
    refStmt.free();
    if (refRow && refRow.jyutping) {
      const initial = refRow.jyutping.charAt(0);
      const sql = `
        SELECT word, jyutping, code
        FROM words
        WHERE jyutping LIKE ?
        ORDER BY word
        LIMIT ? OFFSET ?
      `;
      const stmt = db3.prepare(sql);
      stmt.bind([`${initial}%`, limit, offset]);
      const results = [];
      while (stmt.step()) {
        const row = stmt.getAsObject();
        results.push({
          word: row.word,
          jyutping: row.jyutping,
          code: row.code,
          score: 0
        });
      }
      stmt.free();
      return { items: results };
    }
  }
  if (code_prefix && ref_literal && dimension === "final") {
    const refSql = "SELECT jyutping FROM words WHERE char = ?";
    const refStmt = db3.prepare(refSql);
    refStmt.bind([ref_literal]);
    const refRow = refStmt.step() ? refStmt.getAsObject() : null;
    refStmt.free();
    if (refRow && refRow.jyutping) {
      const sql = `
        SELECT word, jyutping, code
        FROM words
        WHERE jyutping LIKE ?
        ORDER BY word
        LIMIT ? OFFSET ?
      `;
      const stmt = db3.prepare(sql);
      stmt.bind([`%${refRow.jyutping.slice(-1)}`, limit, offset]);
      const results = [];
      while (stmt.step()) {
        const row = stmt.getAsObject();
        results.push({
          word: row.word,
          jyutping: row.jyutping,
          code: row.code,
          score: 0
        });
      }
      stmt.free();
      return { items: results };
    }
  }
  return executeMaskFamily(parsed, db3, mode, limit, offset);
}
function executeMaskFamily(parsed, db3, mode, limit, offset) {
  const pattern = parsed.raw_q.replace(/\?/g, "_").replace(/\*/g, "%").replace(/_%/g, "_");
  const sql = `
    SELECT word, jyutping, code 
    FROM words 
    WHERE code LIKE ? OR word LIKE ?
    ORDER BY word 
    LIMIT ? OFFSET ?
  `;
  const stmt = db3.prepare(sql);
  const results = [];
  stmt.bind([pattern, pattern, limit, offset]);
  while (stmt.step()) {
    const row = stmt.getAsObject();
    results.push({
      word: row.word,
      jyutping: row.jyutping,
      code: row.code,
      score: 0
    });
  }
  stmt.free();
  return { items: results };
}
function executeRelationLookup(parsed, db3, mode, limit, offset) {
  return {
    items: [],
    hint: "\u8FD1\u53CD\u7FA9\u6A21\u5F0F\u529F\u80FD\u6B63\u5728\u958B\u767C\u4E2D..."
  };
}
async function searchWords(q = null, code, char, mode = "0243", limit = 100, offset = 0) {
  const result = await queryEngine.execute({
    q: q || void 0,
    code,
    char,
    mode,
    limit,
    offset
  });
  return result.items;
}
var QueryKind, RouteKind, QUERY_KIND_META, MASK_FAMILY_KINDS, MATCH_SPEC_KINDS, CODE_TAIL_MIDDLE, HYBRID_TAIL_EQUALS_RE, CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT, QueryEngine, queryEngine;
var init_query_engine = __esm({
  "src/db/query-engine.ts"() {
    init_init();
    QueryKind = /* @__PURE__ */ ((QueryKind2) => {
      QueryKind2["RELATION_LOOKUP"] = "relation_lookup";
      QueryKind2["COMPOUND_ANT"] = "compound_ant";
      QueryKind2["COMPOUND_SYN"] = "compound_syn";
      QueryKind2["HYBRID_TAIL_EQUALS_ALIAS"] = "hybrid_tail_equals_alias";
      QueryKind2["EQUALS"] = "equals";
      QueryKind2["PLUS_ANCHOR"] = "plus_anchor";
      QueryKind2["WILDCARD_CODE_ANCHOR"] = "wildcard_code_anchor";
      QueryKind2["CODE_REF_MIDDLE_RHYME"] = "code_ref_middle_rhyme";
      QueryKind2["SERIAL_PHONEME"] = "serial_phoneme";
      QueryKind2["PREFIX_WILDCARD_EQUALS"] = "prefix_wildcard_equals";
      QueryKind2["PARTIAL_RHYME_MASK"] = "partial_rhyme_mask";
      QueryKind2["PARTIAL_INITIAL_MASK"] = "partial_initial_mask";
      QueryKind2["LITERAL_REF"] = "literal_ref";
      QueryKind2["RHYME_ANCHOR"] = "rhyme_anchor";
      QueryKind2["TRIPLE_RHYME_ANCHOR"] = "triple_rhyme_anchor";
      QueryKind2["JYUTPING_ANCHOR"] = "jyutping_anchor";
      QueryKind2["HYBRID_CODE"] = "hybrid_code";
      QueryKind2["MASK"] = "mask";
      QueryKind2["DIGIT_CODE"] = "digit_code";
      QueryKind2["WORD_LOOKUP"] = "word_lookup";
      QueryKind2["JYUTPING_FRAGMENT"] = "jyutping_fragment";
      QueryKind2["UNMATCHED"] = "unmatched";
      return QueryKind2;
    })(QueryKind || {});
    RouteKind = /* @__PURE__ */ ((RouteKind2) => {
      RouteKind2["DIGIT"] = "digit";
      RouteKind2["MASK_FAMILY"] = "mask_family";
      RouteKind2["RELATION"] = "relation";
      RouteKind2["LOOKUP"] = "lookup";
      RouteKind2["UNMATCHED"] = "unmatched";
      RouteKind2["EMPTY"] = "empty";
      return RouteKind2;
    })(RouteKind || {});
    QUERY_KIND_META = {
      ["relation_lookup" /* RELATION_LOOKUP */]: { route: "relation" /* RELATION */ },
      ["compound_syn" /* COMPOUND_SYN */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["compound_ant" /* COMPOUND_ANT */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["hybrid_tail_equals_alias" /* HYBRID_TAIL_EQUALS_ALIAS */]: { route: "mask_family" /* MASK_FAMILY */ },
      ["equals" /* EQUALS */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["prefix_wildcard_equals" /* PREFIX_WILDCARD_EQUALS */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["partial_rhyme_mask" /* PARTIAL_RHYME_MASK */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["partial_initial_mask" /* PARTIAL_INITIAL_MASK */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["serial_phoneme" /* SERIAL_PHONEME */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["plus_anchor" /* PLUS_ANCHOR */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["wildcard_code_anchor" /* WILDCARD_CODE_ANCHOR */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["code_ref_middle_rhyme" /* CODE_REF_MIDDLE_RHYME */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["literal_ref" /* LITERAL_REF */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["rhyme_anchor" /* RHYME_ANCHOR */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["triple_rhyme_anchor" /* TRIPLE_RHYME_ANCHOR */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["jyutping_anchor" /* JYUTPING_ANCHOR */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["hybrid_code" /* HYBRID_CODE */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["mask" /* MASK */]: { route: "mask_family" /* MASK_FAMILY */, match_spec: true },
      ["digit_code" /* DIGIT_CODE */]: { route: "digit" /* DIGIT */ },
      ["word_lookup" /* WORD_LOOKUP */]: { route: "lookup" /* LOOKUP */ },
      ["jyutping_fragment" /* JYUTPING_FRAGMENT */]: { route: "lookup" /* LOOKUP */ },
      ["unmatched" /* UNMATCHED */]: { route: "unmatched" /* UNMATCHED */ }
    };
    MASK_FAMILY_KINDS = new Set(
      Object.entries(QUERY_KIND_META).filter(([_, m]) => m.route === "mask_family" /* MASK_FAMILY */).map(([k]) => k)
    );
    MATCH_SPEC_KINDS = new Set(
      Object.entries(QUERY_KIND_META).filter(([_, m]) => m.match_spec).map(([k]) => k)
    );
    CODE_TAIL_MIDDLE = "\u2215";
    HYBRID_TAIL_EQUALS_RE = /^(\d+)([\u4e00-\u9fff])=$/;
    CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT = "\u300C{literal}\u300D\u6709\u6536\u9304\uFF0C\u4F46\u5728 0243 \u78BC {code} \u4E0B\u7121\u6574\u8A5E\u540C\u97FB\u7D50\u679C\u3002";
    QueryEngine = class {
      db = null;
      /**
       * Execute a search query
       */
      async execute(ctx) {
        if (!isDatabaseInitialized()) {
          await initializeDatabase();
        }
        this.db = getDatabase();
        if (!this.db) {
          return { items: [], hint: "\u8CC7\u6599\u5EAB\u521D\u59CB\u5316\u5931\u6557" };
        }
        const dbCtx = { ...ctx, db: this.db };
        if (!ctx.q) {
          return executeListFilter(this.db, ctx);
        }
        const q = normalizeQuery(ctx.q);
        if (ctx.mode === "syn") {
          return this.dispatchSynMode({ ...ctx, q }, dbCtx);
        }
        const parsed = normalizeAndParse(ctx.q);
        return await dispatch(parsed, dbCtx);
      }
      /**
       * Dispatch synonym mode queries
       */
      async dispatchSynMode(ctx, dbCtx) {
        const parsed = normalizeAndParse(ctx.q);
        return await dispatch(parsed, dbCtx);
      }
    };
    queryEngine = new QueryEngine();
  }
});

// scripts/golden-parity-run.ts
import fs from "node:fs";
var dbPath = process.argv[2];
var casesPath = process.argv[3];
if (!dbPath || !casesPath) {
  console.error("usage: golden-parity-run.ts <db-path> <cases.json>");
  process.exit(2);
}
var cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));
var buf = fs.readFileSync(dbPath);
var initSqlJs2 = (await import("sql.js")).default;
var SQL = await initSqlJs2();
var db2 = new SQL.Database(buf);
var initMod = await Promise.resolve().then(() => (init_init(), init_exports));
initMod.isDatabaseInitialized = () => true;
initMod.getDatabase = () => db2;
initMod.initializeDatabase = async () => db2;
var { queryEngine: queryEngine2, normalizeAndParse: normalizeAndParse2 } = await Promise.resolve().then(() => (init_query_engine(), query_engine_exports));
var out = [];
for (const c of cases) {
  try {
    const parsed = normalizeAndParse2(c.query);
    const result = await queryEngine2.execute({
      q: c.query,
      mode: c.mode,
      limit: 10,
      offset: 0
    });
    const chars = result.items.map((r) => r.word).filter((w) => Boolean(w));
    out.push({
      id: c.id,
      kind: String(parsed.kind),
      chars,
      hint: result.hint ?? null,
      error: null
    });
  } catch (e) {
    out.push({
      id: c.id,
      kind: "",
      chars: [],
      hint: null,
      error: e instanceof Error ? e.message : String(e)
    });
  }
}
process.stdout.write(JSON.stringify(out));
