/** @typedef {'open_search' | 'open_only' | 'close' | 'noop'} ClickAction */

/** @typedef {Object} RawResultRow
 * @property {string} [word]
 * @property {string} [char]
 * @property {string} [jyutping]
 * @property {string} [code]
 * @property {string} [resultType]
 * @property {string} [anchor_dimension]
 * @property {string} [relation]
 */

/** @typedef {Object} MergedListRow
 * @property {string} literal
 * @property {number} readingCount
 * @property {RawResultRow[]} readings
 */

/** @typedef {Object} EntryReading
 * @property {string} jyutping
 * @property {string} code0243
 * @property {string} code02493
 * @property {string[]} initials
 * @property {string[]} finals
 */

/** @typedef {Object} EntryDetailModel
 * @property {string} literal
 * @property {number} length
 * @property {number} corpusWeight
 * @property {EntryReading[]} readings
 * @property {string[]} sources
 * @property {string[]} syns
 * @property {string[]} ants
 */

const TONE_TO_0243 = { 1: '3', 2: '9', 3: '4', 4: '0', 5: '4', 6: '2' };

const SOURCE_FLAG_LABELS = [
  ['hsk30', 1],
  ['kaifang', 2],
  ['rime', 4],
  ['rime_phrase', 8],
  ['rime_words', 16],
  ['words_hk', 32],
];

export function rowLiteral(row) {
  return String(row?.word ?? row?.char ?? '').trim();
}

export function isListableWordRow(row) {
  if (!row || typeof row !== 'object') return false;
  const type = row.resultType;
  if (type && type !== 'word') return false;
  return Boolean(rowLiteral(row));
}

export function mergeResultsByLiteral(rows) {
  const map = new Map();
  for (const row of rows ?? []) {
    if (!isListableWordRow(row)) continue;
    const literal = rowLiteral(row);
    const bucket = map.get(literal) ?? { literal, readings: [] };
    const key = `${literal}\0${row.jyutping ?? ''}\0${row.code ?? ''}`;
    if (!bucket.readings.some((r) => `${rowLiteral(r)}\0${r.jyutping ?? ''}\0${r.code ?? ''}` === key)) {
      bucket.readings.push(row);
    }
    map.set(literal, bucket);
  }
  return [...map.values()].map((item) => ({
    literal: item.literal,
    readingCount: item.readings.length,
    readings: item.readings,
  }));
}

/** @param {{ panelOpen: boolean, activeLiteral: string | null, targetLiteral: string, fromRelationChip?: boolean }} input */
export function resolveListClickAction(input) {
  const literal = String(input.targetLiteral ?? '').trim();
  if (!literal) return 'noop';
  if (input.fromRelationChip) return 'open_search';
  if (!input.panelOpen) return 'open_search';
  if (input.activeLiteral === literal) return 'open_only';
  return 'close';
}

/** @param {{ panelOpen: boolean }} _state */
export function resolveBackdropClickAction(_state) {
  return _state.panelOpen ? 'close' : 'noop';
}

export function code0243FromJyutping(jyutping) {
  if (!jyutping?.trim()) return '';
  return jyutping
    .trim()
    .split(/\s+/)
    .map((syl) => {
      const tone = Number.parseInt(syl[syl.length - 1], 10);
      return TONE_TO_0243[tone] ?? '?';
    })
    .join('');
}

export function parseJsonStringList(raw) {
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === 'string' && raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  return [];
}

export function decodeSourceFlags(flags) {
  const n = Number(flags) || 0;
  if (!n) return [];
  return SOURCE_FLAG_LABELS.filter(([, bit]) => n & bit).map(([label]) => label);
}

/** Sort readings: essay desc → curated → pron rank asc → jyutping */
export function sortReadingRows(rows, signals = {}) {
  const essay = signals.essay ?? {};
  const curated = new Set(signals.curated ?? []);
  const pron = signals.pronRank ?? {};
  const pronRank = (literal, jyut) => pron[`${literal}\t${jyut}`] ?? 99;
  return [...rows].sort((a, b) => {
    const la = rowLiteral(a);
    const lb = rowLiteral(b);
    const ja = String(a.jyutping ?? '');
    const jb = String(b.jyutping ?? '');
    const ea = essay[la] ?? 0;
    const eb = essay[lb] ?? 0;
    if (ea !== eb) return eb - ea;
    const ca = curated.has(la) ? 1 : 0;
    const cb = curated.has(lb) ? 1 : 0;
    if (ca !== cb) return cb - ca;
    const pa = pronRank(la, ja);
    const pb = pronRank(lb, jb);
    if (pa !== pb) return pa - pb;
    return ja.localeCompare(jb);
  });
}

export function buildEntryReading(row) {
  const jyutping = String(row.jyutping ?? '');
  const code0243 = String(row.code ?? '');
  return {
    jyutping,
    code0243,
    code02493: code0243FromJyutping(jyutping) || code0243,
    initials: parseJsonStringList(row.initials),
    finals: parseJsonStringList(row.finals),
  };
}

export function buildEntryDetailModel(payload) {
  const literal = String(payload?.literal ?? '').trim();
  const sorted = sortReadingRows(payload?.readings ?? [], payload?.signals ?? {});
  const flagUnion = (payload?.readings ?? []).reduce((acc, row) => acc | (Number(row.source_flags) || 0), 0);
  return {
    literal,
    length: Number(payload?.length) || [...literal].length,
    corpusWeight: Number(payload?.corpusWeight) || 0,
    readings: sorted.map(buildEntryReading),
    sources: decodeSourceFlags(flagUnion),
    syns: (payload?.syns ?? []).map(String).filter(Boolean),
    ants: (payload?.ants ?? []).map(String).filter(Boolean),
  };
}

/** Sync model from list-click rows — no DB round-trip. */
export function buildEntryDetailModelFromPick(literal, readings, options = {}) {
  const text = String(literal ?? '').trim();
  if (!text || !readings?.length) return null;
  const rows = readings.map((r) => ({
    word: text,
    char: text,
    jyutping: r.jyutping ?? '',
    code: r.code ?? '',
    initials: r.initials,
    finals: r.finals,
    source_flags: r.source_flags,
  }));
  return buildEntryDetailModel({
    literal: text,
    length: options.length ?? [...text].length,
    corpusWeight: options.corpusWeight ?? 0,
    readings: rows,
    syns: [],
    ants: [],
    signals: options.signals ?? {},
  });
}

export function pickPreferredReadingIndex(readings, clickedJyutping) {
  if (!clickedJyutping || !readings?.length) return 0;
  const idx = readings.findIndex((r) => r.jyutping === clickedJyutping);
  return idx >= 0 ? idx : 0;
}

/** ponytail: runnable self-check — `node frontend/entry-detail-core.mjs` */
export function entryDetailCoreSelfCheck() {
  const rows = [
    { word: '就', jyutping: 'zau6', code: '42' },
    { word: '就', jyutping: 'zau2', code: '69' },
    { word: '香港', jyutping: 'hoeng1 gong2', code: '39' },
  ];
  const merged = mergeResultsByLiteral(rows);
  if (merged.length !== 2 || merged[0].readingCount !== 2) {
    throw new Error('mergeResultsByLiteral failed');
  }
  if (resolveListClickAction({ panelOpen: false, activeLiteral: null, targetLiteral: '就' }) !== 'open_search') {
    throw new Error('resolveListClickAction closed');
  }
  if (resolveListClickAction({ panelOpen: true, activeLiteral: '就', targetLiteral: '就' }) !== 'open_only') {
    throw new Error('resolveListClickAction same literal');
  }
  if (resolveListClickAction({ panelOpen: true, activeLiteral: '就', targetLiteral: '香港' }) !== 'close') {
    throw new Error('resolveListClickAction different literal');
  }
  if (code0243FromJyutping('hoeng1 gong2') !== '39') {
    throw new Error('code0243FromJyutping');
  }
}

