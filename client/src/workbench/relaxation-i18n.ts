import type { RelaxationKind } from './contracts.ts';

const LABELS_ZH: Record<RelaxationKind, string> = {
  remove_code: '暫時唔限定聲調碼',
  remove_final: '暫時唔跟同韻',
  remove_initial: '暫時唔跟同聲',
  semantic_ranked: '容許更廣嘅近義排序',
  loosen_mode: '放寬聲調精度一檔',
};

const LABELS_EN: Record<RelaxationKind, string> = {
  remove_code: 'Drop tone-code matching for now',
  remove_final: 'Drop same-rhyme matching for now',
  remove_initial: 'Drop same-initial matching for now',
  semantic_ranked: 'Allow a broader synonym ranking',
  loosen_mode: 'Loosen tone precision by one step',
};

export function relaxationKindLabel(kind: RelaxationKind, lang: 'zh' | 'en' = 'zh'): string {
  return (lang === 'en' ? LABELS_EN : LABELS_ZH)[kind];
}
