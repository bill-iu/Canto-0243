/**
 * 韻母比對檔 — shared expand tables (ADR-0078).
 * Profiles: exact=正韻, tong=通韻, nucleus=腹韻, coda=尾韻.
 * 通韻：粵曲二十部系命名（部／韻）+ 舒入相配（rhyme2 舒聲 + rhyme.txt 入聲歸部）。
 */

export const RHYME_PROFILES = Object.freeze(['exact', 'tong', 'nucleus', 'coda']);

export const RHYME_PROFILE_LABELS = Object.freeze({
  exact: '正韻',
  tong: '通韻',
  nucleus: '腹韻',
  coda: '尾韻',
});

export function isRhymeProfile(value) {
  return RHYME_PROFILES.includes(value);
}

export function normalizeRhymeProfile(value) {
  return isRhymeProfile(value) ? value : 'exact';
}

/**
 * 通韻部／韻：name 教學標籤；finals 含舒聲＋舒入相配入聲。
 * @type {readonly { readonly name: string, readonly finals: readonly string[] }[]}
 */
export const TONG_CLASSES = Object.freeze([
  // 多韻互通 →「部」；單細韻 →「韻」。入聲併入對應舒聲部（舒入相配）。
  Object.freeze({
    name: '依時部',
    finals: Object.freeze(['i', 'yu', 'eoi', 'ei', 'ip', 'it', 'ik', 'yut', 'eot']),
  }),
  Object.freeze({
    name: '郎當部',
    finals: Object.freeze(['ong', 'on', 'oeng', 'ok', 'ot', 'oek']),
  }),
  Object.freeze({
    name: '民親部',
    finals: Object.freeze(['an', 'ang', 'am', 'at', 'ak', 'ap']),
  }),
  Object.freeze({
    name: '田邊部',
    finals: Object.freeze(['in', 'im', 'yun', 'it', 'ip', 'yut']),
  }),
  Object.freeze({
    name: '欄柵部',
    finals: Object.freeze(['aan', 'aam', 'aang', 'aat', 'aap', 'aak']),
  }),
  Object.freeze({
    name: '勞高部',
    finals: Object.freeze(['ou', 'u', 'uk', 'ut']),
  }),
  Object.freeze({
    name: '裁開部',
    finals: Object.freeze(['oi', 'ui']),
  }),
  Object.freeze({ name: '雞啼韻', finals: Object.freeze(['ai']) }),
  Object.freeze({ name: '倫敦韻', finals: Object.freeze(['eon', 'eot']) }),
  Object.freeze({ name: '盤歡韻', finals: Object.freeze(['un', 'ut']) }),
  Object.freeze({ name: '埋街韻', finals: Object.freeze(['aai']) }),
  Object.freeze({ name: '英明韻', finals: Object.freeze(['ing', 'ik']) }),
  Object.freeze({ name: '靈釘韻', finals: Object.freeze(['eng', 'ek']) }),
  Object.freeze({ name: '優遊韻', finals: Object.freeze(['au']) }),
  Object.freeze({ name: '農工韻', finals: Object.freeze(['ung', 'uk']) }),
  Object.freeze({ name: '逍遙韻', finals: Object.freeze(['iu']) }),
  Object.freeze({
    name: '羅疏韻',
    finals: Object.freeze(['o', 'ok', 'ot', 'op']),
  }),
  Object.freeze({
    name: '麻花韻',
    finals: Object.freeze(['aa', 'aap', 'aat', 'aak']),
  }),
  Object.freeze({ name: '咆哮韻', finals: Object.freeze(['aau']) }),
  Object.freeze({
    name: '斜遮韻',
    finals: Object.freeze(['e', 'ep', 'et', 'ek', 'em', 'en']),
  }),
  Object.freeze({
    name: '靴瘸韻',
    finals: Object.freeze(['oe', 'oek', 'oet']),
  }),
  Object.freeze({ name: '五唔韻', finals: Object.freeze(['m', 'ng']) }),
  Object.freeze({ name: '掉韻', finals: Object.freeze(['eu']) }),
]);

/** @type {readonly (readonly string[])[]} */
const TONG_GROUPS = Object.freeze(TONG_CLASSES.map((c) => c.finals));

/** @type {readonly (readonly string[])[]} */
const NUCLEUS_GROUPS = Object.freeze([
  Object.freeze(['aai']),
  Object.freeze(['aau']),
  Object.freeze(['aa', 'aap', 'aat', 'aak', 'aam', 'aan', 'aang']),
  Object.freeze(['ai']),
  Object.freeze(['au']),
  Object.freeze(['ei']),
  Object.freeze(['eu']),
  Object.freeze(['iu']),
  Object.freeze(['ou']),
  Object.freeze(['oe', 'oek', 'oet', 'oeng']),
  Object.freeze(['eot', 'eon', 'eoi']),
  Object.freeze(['ui']),
  Object.freeze(['ng']),
  Object.freeze(['yu', 'yut', 'yun']),
  Object.freeze(['ap', 'at', 'ak', 'am', 'an', 'ang', 'a']),
  Object.freeze(['e', 'ek', 'eng', 'em', 'en', 'ep', 'et']),
  Object.freeze(['i', 'ip', 'it', 'ik', 'im', 'in', 'ing']),
  Object.freeze(['o', 'ot', 'ok', 'on', 'ong', 'oi', 'op']),
  Object.freeze(['u', 'ut', 'uk', 'un', 'ung']),
  Object.freeze(['m']),
]);

/** @type {readonly (readonly string[])[]} */
const CODA_GROUPS = Object.freeze([
  Object.freeze(['i']),
  Object.freeze(['ip', 'ap', 'aap', 'ep', 'op']),
  Object.freeze(['it', 'yut', 'ut', 'eot', 'oet', 'ot', 'at', 'aat', 'et']),
  Object.freeze(['ik', 'uk', 'ek', 'oek', 'ok', 'ak', 'aak']),
  Object.freeze(['im', 'am', 'aam', 'm', 'em']),
  Object.freeze(['in', 'yun', 'un', 'eon', 'on', 'an', 'aan', 'en']),
  Object.freeze(['ing', 'ung', 'eng', 'oeng', 'ong', 'ang', 'aang', 'ng']),
  Object.freeze(['iu', 'ou', 'au', 'aau', 'eu']),
  Object.freeze(['yu']),
  Object.freeze(['ui', 'ei', 'eoi', 'oi', 'ai', 'aai']),
  Object.freeze(['e']),
  Object.freeze(['oe']),
  Object.freeze(['o']),
  Object.freeze(['aa', 'a']),
  Object.freeze(['u']),
]);

function buildLookup(groups) {
  /** @type {Map<string, ReadonlySet<string>>} */
  const map = new Map();
  for (const group of groups) {
    const set = new Set(group);
    for (const f of group) {
      const prev = map.get(f);
      if (prev) {
        for (const x of set) prev.add(x);
      } else {
        map.set(f, new Set(set));
      }
    }
  }
  return map;
}

const TONG_LOOKUP = buildLookup(TONG_GROUPS);
const NUCLEUS_LOOKUP = buildLookup(NUCLEUS_GROUPS);
const CODA_LOOKUP = buildLookup(CODA_GROUPS);

function lookupFor(profile) {
  if (profile === 'tong') return TONG_LOOKUP;
  if (profile === 'nucleus') return NUCLEUS_LOOKUP;
  if (profile === 'coda') return CODA_LOOKUP;
  return null;
}

/**
 * Guide render: { name, finals }[]
 * tong uses TONG_CLASSES; nucleus/coda unnamed numbered; exact each final alone.
 */
export function rhymeClassesForProfile(profile) {
  const p = normalizeRhymeProfile(profile);
  if (p === 'tong') return TONG_CLASSES;
  if (p === 'nucleus') {
    return Object.freeze(
      NUCLEUS_GROUPS.map((finals, i) =>
        Object.freeze({ name: `腹${i + 1}`, finals }),
      ),
    );
  }
  if (p === 'coda') {
    return Object.freeze(
      CODA_GROUPS.map((finals, i) =>
        Object.freeze({ name: `尾${i + 1}`, finals }),
      ),
    );
  }
  const all = new Set();
  for (const g of TONG_GROUPS) for (const f of g) all.add(f);
  for (const g of NUCLEUS_GROUPS) for (const f of g) all.add(f);
  for (const g of CODA_GROUPS) for (const f of g) all.add(f);
  return Object.freeze(
    [...all].sort().map((f) => Object.freeze({ name: f, finals: Object.freeze([f]) })),
  );
}

/** @deprecated use rhymeClassesForProfile */
export function rhymeGroupsForProfile(profile) {
  return Object.freeze(rhymeClassesForProfile(profile).map((c) => c.finals));
}

export function rhymeProfileGuideOrder() {
  return RHYME_PROFILES;
}

/**
 * 教學用參考字（一韻一字；唔照抄外站字表）。
 * 缺 key 時 UI 只顯示韻母。
 */
export const FINAL_EXAMPLE_CHARS = Object.freeze({
  a: '打',
  aa: '家',
  aai: '買',
  aak: '白',
  aam: '藍',
  aan: '山',
  aang: '橫',
  aap: '鴨',
  aat: '八',
  aau: '包',
  ai: '西',
  ak: '北',
  am: '心',
  an: '新',
  ang: '生',
  ap: '十',
  at: '七',
  au: '手',
  e: '車',
  ei: '飛',
  ek: '尺',
  em: '舐',
  en: '釘',
  eng: '正',
  eoi: '水',
  eon: '春',
  eot: '出',
  ep: '夾',
  et: '捏',
  eu: '掉',
  i: '詩',
  ik: '色',
  im: '點',
  in: '天',
  ing: '星',
  ip: '葉',
  it: '熱',
  iu: '小',
  m: '唔',
  ng: '五',
  o: '多',
  oe: '靴',
  oek: '腳',
  oeng: '香',
  oet: '略',
  oi: '開',
  ok: '學',
  on: '安',
  ong: '方',
  op: '合',
  ot: '渴',
  ou: '好',
  u: '夫',
  ui: '梅',
  uk: '屋',
  un: '門',
  ung: '工',
  ut: '活',
  yu: '魚',
  yun: '遠',
  yut: '月',
});

export function exampleCharForFinal(final) {
  const f = String(final || '').toLowerCase().trim();
  return FINAL_EXAMPLE_CHARS[f] || '';
}

/** Chip label: `i [詩]` */
export function formatFinalWithExample(final) {
  const f = String(final || '').toLowerCase().trim();
  const ch = exampleCharForFinal(f);
  return ch ? `${f} [${ch}]` : f;
}

export function expandOneFinal(final, profile = 'exact') {
  const f = String(final || '').toLowerCase().trim();
  if (!f) return new Set();
  const p = normalizeRhymeProfile(profile);
  if (p === 'exact') return new Set([f]);
  const lookup = lookupFor(p);
  const hit = lookup?.get(f);
  if (hit?.size) return new Set(hit);
  return new Set([f]);
}

export function expandFinalOptions(options, profile = 'exact') {
  const p = normalizeRhymeProfile(profile);
  if (p === 'exact') {
    return options instanceof Set ? new Set(options) : new Set(options || []);
  }
  const out = new Set();
  for (const f of options || []) {
    for (const x of expandOneFinal(f, p)) out.add(x);
  }
  return out;
}

export function finalsCompatible(a, b, profile = 'exact') {
  const fa = String(a || '').toLowerCase();
  const fb = String(b || '').toLowerCase();
  if (!fa || !fb) return false;
  if (normalizeRhymeProfile(profile) === 'exact') return fa === fb;
  const expanded = expandOneFinal(fa, profile);
  return expanded.has(fb);
}
