import type { QueryResult } from './db/query';

/** ponytail: desktop dedupe for flat search rows only; lookup layout keeps all sections */
export function displayResults(results: QueryResult[]): QueryResult[] {
  const seen = new Set<string>();
  return results.filter((row) => {
    if (row.resultType && row.resultType !== 'word') {
      return true;
    }
    const key = row.word;
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function resultKey(row: QueryResult, index: number): string {
  const kind = row.resultType ?? 'word';
  return `${kind}-${row.word}-${row.code}-${index}`;
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
        if (row.resultType === 'code') {
          return (
            <li key={resultKey(row, index)} className="result-item result-item--code">
              <button type="button" className="result-link" onClick={() => onPick(pick)} aria-label={`搜尋碼 ${pick}`}>
                <span className="result-kind">碼</span>
                <span className="code">{row.code || pick}</span>
              </button>
            </li>
          );
        }
        if (row.resultType === 'jyutping') {
          return (
            <li key={resultKey(row, index)} className="result-item result-item--jyutping">
              <button type="button" className="result-link" onClick={() => onPick(pick)} aria-label={`搜尋粵拼 ${pick}`}>
                <span className="result-kind">粵拼</span>
                <span className="jyutping">{row.jyutping || pick}</span>
              </button>
            </li>
          );
        }
        return (
          <li key={resultKey(row, index)} className="result-item">
            <button
              type="button"
              className="result-link result-link--word"
              onClick={() => onPick(pick)}
              aria-label={`搜尋 ${pick}`}
            >
              <span className="word">{row.word}</span>
            </button>
            {row.jyutping ? <span className="jyutping">{row.jyutping}</span> : null}
            {row.code ? <span className="code">{row.code}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}
