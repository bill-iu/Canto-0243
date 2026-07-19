import { initRankingData } from '../src/db/ranking.ts';
import { resolveLineReadingsFromRows } from '../src/workbench/pwa-line-readings.ts';

declare const process: { argv: string[] };
declare const Buffer: { from(value: string, encoding: 'base64'): { toString(encoding: 'utf8'): string } };

const raw = Buffer.from(process.argv[2] ?? 'e30=', 'base64').toString('utf8');
const payload = JSON.parse(raw) as {
  surface: string;
  rows: Array<{ char: string; jyutping: string; code: string }>;
  pronRank?: Record<string, number>;
};

initRankingData({ pronRank: payload.pronRank ?? {} });
const result = resolveLineReadingsFromRows(payload.surface, payload.rows);
console.log(JSON.stringify(result));
