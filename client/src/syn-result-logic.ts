import type { QueryResult } from './db/query';
import { getResultStatsCopy } from '../../shared/result-stats-i18n.mjs';

export function synResultItemCount(results: QueryResult[]): number {
  return results.filter(
    (r) => r.relation === 'syn' || r.relation === 'ant' || r.relation === 'semantic_related',
  ).length;
}

export function synResultsStats(results: QueryResult[], lang = 'zh'): string {
  const syns = results.filter((r) => r.relation === 'syn').length;
  const ants = results.filter((r) => r.relation === 'ant').length;
  const related = results.filter((r) => r.relation === 'semantic_related').length;
  return getResultStatsCopy(lang).semantic(syns, ants, related, results.length);
}
