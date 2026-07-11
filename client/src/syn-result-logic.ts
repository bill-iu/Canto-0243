import type { QueryResult } from './db/query';

export function synResultItemCount(results: QueryResult[]): number {
  return results.filter(
    (r) => r.relation === 'syn' || r.relation === 'ant' || r.relation === 'semantic_related',
  ).length;
}

export function synResultsStats(results: QueryResult[]): string {
  const syns = results.filter((r) => r.relation === 'syn').length;
  const ants = results.filter((r) => r.relation === 'ant').length;
  const related = results.filter((r) => r.relation === 'semantic_related').length;
  let text = `近義 ${syns}　反義 ${ants}`;
  if (related > 0) {
    text += `　語意相關 ${related}`;
  }
  return `${text}（已載入 ${results.length}）`;
}
