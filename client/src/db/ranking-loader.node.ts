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
    const word = parts[0]!.trim();
    const freq = Number.parseInt(parts[1]!.trim(), 10);
    if (!word || Number.isNaN(freq) || freq < 0) {
      continue;
    }
    out[word] = freq;
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

/** Load ranking signals from repo data/ (call before query-engine in Node runners). */
export function loadRankingData(repoRoot: string): void {
  const root = path.resolve(repoRoot);
  const charCsv = fs.readFileSync(path.join(root, 'data/rime/char.csv'), 'utf8');
  const essayPath = path.join(root, 'data/essay/essay-cantonese.txt');
  const curatedPath = path.join(root, 'data/lexicon/curated_common.txt');

  const essay = fs.existsSync(essayPath)
    ? parseEssayCorpus(fs.readFileSync(essayPath, 'utf8'))
    : {};
  const curated = fs.existsSync(curatedPath)
    ? parseCuratedList(fs.readFileSync(curatedPath, 'utf8'))
    : [];

  initRankingData({
    essay,
    curated,
    pronRank: parseCharCsv(charCsv),
  });
}
