import type { CandidateReasonKind } from './contracts.ts';

const LABELS_ZH: Record<CandidateReasonKind, string> = {
  tone_exact: '聲調精確符合',
  tone_loose: '聲調按目前檔位鬆配',
  literal_match: '保留指定字面',
  same_final: '韻母相同',
  same_initial: '聲母相同',
  direct_syn: '直接近義',
  semantic_related: '語意相關',
  frequency_rank: '按詞頻與權威讀音排序',
  relaxed_constraint: '使用已確認的放寬條件',
};

const LABELS_ZH_HANS: Record<CandidateReasonKind, string> = {
  tone_exact: '声调精确符合',
  tone_loose: '声调按目前档位松配',
  literal_match: '保留指定字面',
  same_final: '韵母相同',
  same_initial: '声母相同',
  direct_syn: '直接近义',
  semantic_related: '语意相关',
  frequency_rank: '按词频与权威读音排序',
  relaxed_constraint: '使用已确认的放宽条件',
};

export function candidateReasonLabel(kind: CandidateReasonKind, lang: 'zh' | 'zh-Hans' = 'zh'): string {
  return (lang === 'zh-Hans' ? LABELS_ZH_HANS : LABELS_ZH)[kind];
}
