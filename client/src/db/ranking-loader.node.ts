/**
 * Node-only ranking data loader for golden parity.
 * ponytail: browser PWA upgrade path — bundle ranking-index.json at build
 */
import fs from 'node:fs';
import path from 'node:path';

import { initRankingData, PRON_RANK_SORT } from './ranking.ts';

function parseCharCsv(csvText: string): Record<string, number> {
  const out: Record<string, number> = {};
  const lines = csvText.split(/\r?\n/);
  if (!lines.length) {
    return out;
  }
  const header = lines[0]!.split(',');
  const charIdx = header.indexOf('char');
  const jyutIdx = header.indexOf('jyutping');
  const rankIdx = header.indexOf('pron_rank');
  if (charIdx < 0 || jyutIdx < 0 || rankIdx < 0) {
    return out;
  }
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]!.trim();
    if (!line) {
      continue;
    }
    const cols = line.split(',');
    const ch = (cols[charIdx] ?? '').trim();
    const jyut = (cols[jyutIdx] ?? '').trim();
    const rankLabel = (cols[rankIdx] ?? '').trim();
    if (!ch || !jyut || ch.length !== 1) {
      continue;
    }
    const rankVal = PRON_RANK_SORT[rankLabel] ?? 99;
    out[`${ch}\t${jyut}`] = rankVal;
  }
  return out;
}

function parseEssayCorpus(text: string): Record<string, number> {
  const out: Record<string, number> = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    const parts = trimmed.split('\t');
    if (parts.length < 2) {
      continue;
    }
    // HK orthography: 覈 → 核 (matches OpenCC HKVariants / app.utils.trad_chinese)
    const word = parts[0]!.trim().replace(/覈/g, '核');
    const freq = Number.parseInt(parts[1]!.trim(), 10);
    if (!word || Number.isNaN(freq) || freq < 0) {
      continue;
    }
    out[word] = Math.max(out[word] ?? 0, freq);
  }
  return out;
}

function parseCuratedList(text: string): string[] {
  const out: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const w = line.trim();
    if (!w || w.startsWith('#')) {
      continue;
    }
    out.push(w);
  }
  return out;
}

export function parseWordPronRanks(text: string): Record<string, number> {
  const rows: unknown = JSON.parse(text);
  if (!Array.isArray(rows)) throw new Error('Word reading ranks must be a list');
  const out: Record<string, number> = {};
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error('Invalid word reading rank row');
    const actualValue = row.ingested_char === undefined ? row.char : row.ingested_char;
    if (typeof row.char !== 'string' || typeof actualValue !== 'string' || typeof row.jyutping !== 'string' ||
        typeof row.pron_rank !== 'string' || !Object.hasOwn(PRON_RANK_SORT, row.pron_rank)) {
      throw new Error('Invalid word reading rank fields');
    }
    const char = row.char.trim();
    const actual = actualValue.trim();
    const jyut = row.jyutping.trim().replace(/\s+/g, ' ');
    const value = PRON_RANK_SORT[row.pron_rank]!;
    if ([...char].length < 2 || [...actual].length !== [...char].length ||
        [...char].length !== jyut.split(' ').length || !/^[a-z]+[1-6](?: [a-z]+[1-6])*$/.test(jyut)) {
      throw new Error(`Invalid word reading rank for ${char}`);
    }
    for (const literal of [char, actual]) {
      const key = `${literal}\t${jyut}`;
      if (out[key] !== undefined && out[key] !== value) throw new Error(`Conflicting word reading rank for ${literal}`);
      out[key] = value;
    }
  }
  return out;
}

/** Load ranking signals from repo data/ (call before query-engine in Node runners). */
export function buildRankingData(repoRoot: string): {
  essay: Record<string, number>;
  curated: string[];
  pronRank: Record<string, number>;
} {
  const root = path.resolve(repoRoot);
  const charCsv = fs.readFileSync(path.join(root, 'data/rime/char.csv'), 'utf8');
  const essayPath = path.join(root, 'data/essay/essay-cantonese.txt');
  const curatedPath = path.join(root, 'data/lexicon/curated_common.txt');
  const wordRanksPath = path.join(root, 'data/lexicon/curated_reading_ranks.json');

  const essay = fs.existsSync(essayPath)
    ? parseEssayCorpus(fs.readFileSync(essayPath, 'utf8'))
    : {};
  const curated = fs.existsSync(curatedPath)
    ? parseCuratedList(fs.readFileSync(curatedPath, 'utf8'))
    : [];

  return {
    essay,
    curated,
    pronRank: { ...parseCharCsv(charCsv), ...parseWordPronRanks(fs.readFileSync(wordRanksPath, 'utf8')) },
  };
}

export function loadRankingData(repoRoot: string): void {
  initRankingData(buildRankingData(repoRoot));
}
