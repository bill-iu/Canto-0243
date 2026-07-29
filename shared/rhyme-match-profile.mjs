/**
 * 韻母比對檔 — shared expand tables (ADR-0078).
 * Profiles: exact=正韻, tong=通韻, nucleus=腹韻, coda=尾韻.
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

/** @type {readonly (readonly string[])[]} */
const TONG_GROUPS = Object.freeze([
  // 舒聲傳統韻部（參考 m2）
  Object.freeze(['i', 'ei', 'yu', 'eoi', 'ai']), // 雞啼
  Object.freeze(['oeng', 'on', 'ong']), // 陽光
  Object.freeze(['an', 'am', 'ang']), // 親琴
  Object.freeze(['aa']), // 麻花
  Object.freeze(['in', 'im', 'yun']), // 添邊
  Object.freeze(['ing']), // 英明
  Object.freeze(['eng']), // 醒靈
  Object.freeze(['aam', 'aan', 'aang']), // 懶珊
  Object.freeze(['ung']), // 農工
  Object.freeze(['oi', 'ui']), // 杯開
  Object.freeze(['aai']), // 埋街
  Object.freeze(['iu']), // 逍遙
  Object.freeze(['ou', 'u']), // 扶高
  Object.freeze(['o']), // 多和
  Object.freeze(['au']), // 優遊
  Object.freeze(['aau']), // 拋錨
  Object.freeze(['e']), // 車斜
  Object.freeze(['eon']), // 倫敦
  Object.freeze(['un']), // 歡門
  Object.freeze(['oe']), // 靴瘸
  // 入聲搜尋歸組（參考 m2a；併入共母音部）
  Object.freeze(['aa', 'aap', 'aat', 'aak']),
  Object.freeze(['a', 'ap', 'at', 'ak']),
  Object.freeze(['e', 'ek', 'ep', 'et', 'em', 'en', 'eng']),
  Object.freeze(['i', 'ip', 'it', 'ik', 'im', 'in', 'ing']),
  Object.freeze(['o', 'ok', 'ot', 'op', 'on', 'ong', 'oi']),
  Object.freeze(['oe', 'oek', 'oet', 'oeng', 'eot', 'eon', 'eoi']),
  Object.freeze(['u', 'ut', 'uk', 'un', 'ung', 'ou']),
  Object.freeze(['yu', 'yut', 'yun']),
  Object.freeze(['m', 'ng']),
  Object.freeze(['eu']),
]);

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
  // freeze-ish: return Map of Sets
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

/** Guide / docs: group lists for a profile (C3′ single-source render). */
export function rhymeGroupsForProfile(profile) {
  const p = normalizeRhymeProfile(profile);
  if (p === 'tong') return TONG_GROUPS;
  if (p === 'nucleus') return NUCLEUS_GROUPS;
  if (p === 'coda') return CODA_GROUPS;
  // exact: each known final is its own group (union of table members, sorted)
  const all = new Set();
  for (const g of TONG_GROUPS) for (const f of g) all.add(f);
  for (const g of NUCLEUS_GROUPS) for (const f of g) all.add(f);
  for (const g of CODA_GROUPS) for (const f of g) all.add(f);
  return Object.freeze([...all].sort().map((f) => Object.freeze([f])));
}

export function rhymeProfileGuideOrder() {
  return RHYME_PROFILES;
}

/**
 * Expand one final (tone-stripped jyutping final) to the match set for profile.
 * Unknown finals fall back to singleton (正韻 behaviour).
 */
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

/** Expand a set of exact finals under the current profile. */
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
