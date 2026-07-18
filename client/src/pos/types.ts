/** 專案自建詞性 — carrier + formal set (CONTEXT § 詞性與分類). */

export type FormalPos = 'n' | 'v' | 'a' | 'r' | 'x';
export type PosCode = FormalPos | 'u';
export type PosFamily = 'idiom';
export type PosVoice = 'active' | 'passive';

export type PosEntry = {
  pos: readonly PosCode[];
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
};

export const VOICE_LABEL_ZH: Record<PosVoice, string> = {
  active: '主動',
  passive: '被動',
};
