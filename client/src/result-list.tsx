import type { QueryResult } from './db/query';

/** ponytail: PWA 只渲染 word 列；碼／粵拼內嵌於詞條行（唔出 Portable 標題列） */
export function displayResults(results: QueryResult[]): QueryResult[] {
  const seen = new Set<string>();
  return results.filter((row) => {
    if (row.resultType && row.resultType !== 'word') {
      return false;
    }
    const key = `${row.word}\0${row.jyutping ?? ''}\0${row.code ?? ''}`;
    if (!row.word || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function resultKey(row: QueryResult, index: number): string {
  return `word-${row.word}-${row.code}-${row.jyutping}-${index}`;
}

export function ResultList({
  results,
  onPick,
}: {
  results: QueryResult[];
  onPick: (query: string) => void;
}) {
  const rows = displayResults(results);
  if (!rows.length) {
    return null;
  }

  return (
    <ul className="results-list-items">
      {rows.map((row, index) => {
        const pick = row.word;
        return (
          <li key={resultKey(row, index)} className="result-item">
            <button
              type="button"
              className="result-link"
              onClick={() => onPick(pick)}
              aria-label={`搜尋 ${pick}${row.jyutping ? ` ${row.jyutping}` : ''}${row.code ? ` ${row.code}` : ''}`}
            >
              <span className="word">{row.word}</span>
              {(row.jyutping || row.code) && (
                <span className="result-meta">
                  {row.jyutping ? <span className="jyutping">{row.jyutping}</span> : null}
                  {row.code ? <span className="code">{row.code}</span> : null}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
