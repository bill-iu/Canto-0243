import type { QueryResult } from './db/query';

function sectionTitle(title: string, count: number): string {
  return count > 0 ? `${title} (${count})` : title;
}

function itemTitle(row: QueryResult): string {
  const parts: string[] = [];
  if (row.source) {
    parts.push(`來源：${row.source}`);
  }
  if (row.in_db === false) {
    parts.push('外部詞庫');
  }
  return parts.join(' · ');
}

function SynSection({
  title,
  items,
  onPick,
}: {
  title: string;
  items: QueryResult[];
  onPick: (query: string) => void;
}) {
  return (
    <section className="syn-section">
      <h2 className="syn-section__title">{sectionTitle(title, items.length)}</h2>
      <div className="syn-section__grid">
        {items.length > 0 ? (
          items.map((row, index) => (
            <button
              key={`${row.word}-${index}`}
              type="button"
              className="syn-chip"
              title={itemTitle(row) || undefined}
              onClick={() => onPick(row.word)}
              aria-label={`搜尋 ${row.word}`}
            >
              {row.word}
              {row.in_db === false ? <span className="syn-chip__badge">外部</span> : null}
            </button>
          ))
        ) : (
          <p className="syn-empty">無可用結果</p>
        )}
      </div>
    </section>
  );
}

export function SynResultList({
  results,
  onPick,
}: {
  results: QueryResult[];
  onPick: (query: string) => void;
}) {
  const syns = results.filter((r) => r.relation === 'syn');
  const ants = results.filter((r) => r.relation === 'ant');
  const related = results.filter((r) => r.relation === 'semantic_related');

  return (
    <div className="syn-container">
      <SynSection title="近義詞" items={syns} onPick={onPick} />
      <SynSection title="反義詞" items={ants} onPick={onPick} />
      {related.length > 0 ? <SynSection title="語意相關" items={related} onPick={onPick} /> : null}
    </div>
  );
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
