/** 專案自建詞性 — carrier + formal set (CONTEXT § 詞性與分類 / 詞性信任). */

export type FormalPos = 'n' | 'v' | 'a' | 'r' | 'x';
export type PosCode = FormalPos | 'u';
export type PosFamily = 'idiom' | 'chengyu' | 'suyu' | 'yanyu' | 'xiehouyu';
export type PosVoice = 'active' | 'passive';
/** high = 展示+閘; medium = 閘 only; low = 起草/缺標 */
export type PosTrust = 'high' | 'medium' | 'low';

export type PosEntry = {
  /** Raw codes on SSOT row (may include low-trust COW drafts). */
  pos: readonly PosCode[];
  trust?: PosTrust;
  /** 閘用詞類 (high|medium); seed/campaign gate path — not creator filter alone */
  gate?: readonly FormalPos[];
  /** High-trust display 詞類; creator filter/display also union raw `pos` (any trust) */
  show?: readonly FormalPos[];
  family?: PosFamily;
  voice?: PosVoice;
};

export type ProjectPosCarrier = {
  version: string;
  p0HardGate: boolean;
  literals: Record<string, PosEntry>;
};

export const FORMAL_POS = new Set<string>(['n', 'v', 'a', 'r', 'x']);

export const POS_LABEL_ZH: Record<PosCode, string> = {
  n: '名',
  v: '動',
  a: '形',
  r: '副',
  x: '虛',
  u: '未定',
};

export const FAMILY_LABEL_ZH: Record<PosFamily, string> = {
  idiom: '熟語',
  chengyu: '成語',
  suyu: '俗語',
  yanyu: '諺語',
  xiehouyu: '歇後語',
};

export const VOICE_LABEL_ZH: Record<PosVoice, string> = {
  active: '主動',
  passive: '被動',
};
