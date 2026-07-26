import type { RelaxationKind } from './contracts.ts';

const LABELS_ZH: Record<RelaxationKind, string> = {
  remove_code: '暫時唔限定聲調碼',
  remove_final: '暫時唔跟同韻',
  remove_initial: '暫時唔跟同聲',
  semantic_ranked: '容許更廣嘅近義排序',
  loosen_mode: '放寬聲調精度一檔',
};

const LABELS_ZH_HANS: Record<RelaxationKind, string> = {
  remove_code: '暂时唔限定声调码',
  remove_final: '暂时唔跟同韵',
  remove_initial: '暂时唔跟同声',
  semantic_ranked: '容许更广嘅近义排序',
  loosen_mode: '放宽声调精度一档',
};

const LABELS_EN: Record<RelaxationKind, string> = {
  remove_code: 'Drop tone-code matching for now',
  remove_final: 'Drop same-rhyme matching for now',
  remove_initial: 'Drop same-initial matching for now',
  semantic_ranked: 'Allow a broader synonym ranking',
  loosen_mode: 'Loosen tone precision by one step',
};

export function relaxationKindLabel(kind: RelaxationKind, lang: 'zh' | 'zh-Hans' | 'en' = 'zh'): string {
  return (lang === 'en' ? LABELS_EN : lang === 'zh-Hans' ? LABELS_ZH_HANS : LABELS_ZH)[kind];
}
