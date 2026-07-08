/**
 * Build rhyme-letter index from data/rime/char.csv (Node prebuild / parity runner).
 */
import fs from 'node:fs';
import path from 'node:path';

import {
  isStandaloneNasalSyllableToken,
  splitJyutping,
  STANDALONE_NASAL_FINALS,
  syllableLetters,
} from './jyutping-codec.ts';
import { initRhymeLetterIndex, normalizeRhymeLetters, syllableMatchesRhymeFragment } from './rime-index.ts';

const VOWEL_RHYME_LETTERS = new Set(['a', 'e', 'i', 'o', 'u']);

type RimeEntry = { letters: string; final: string; token: string };

function rankValue(pronRank: string): number {
  if (pronRank === '預設') {
    return 0;
  }
  if (pronRank === '常用') {
    return 1;
  }
  if (pronRank === '罕見') {
    return 2;
  }
  return 99;
}

function tokensToRimeEntries(jyut: string): RimeEntry[] {
  const entries: RimeEntry[] = [];
  for (const token of jyut.split(/\s+/)) {
    const letters = syllableLetters(token);
    if (!letters) {
      continue;
    }
    let final = '';
    if (isStandaloneNasalSyllableToken(token)) {
      final = letters;
    } else {
      const [, finals] = splitJyutping(token);
      final = finals[0] ?? '';
    }
    entries.push({ letters, final, token });
  }
  return entries;
}

function parseCharCsvEntries(csvText: string): RimeEntry[] {
  const rowsByChar = new Map<string, Array<{ rank: number; jyut: string }>>();
  const lines = csvText.split(/\r?\n/);
  if (!lines.length) {
    return [];
  }
  const header = lines[0]!.split(',');
  const charIdx = header.indexOf('char');
  const jyutIdx = header.indexOf('jyutping');
  const rankIdx = header.indexOf('pron_rank');
  if (jyutIdx < 0) {
    return [];
  }
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]!.trim();
    if (!line) {
      continue;
    }
    const cols = line.split(',');
    const ch = (cols[charIdx] ?? '').trim();
    const jyut = (cols[jyutIdx] ?? '').trim();
    const pronRank = rankIdx >= 0 ? (cols[rankIdx] ?? '').trim() : '預設';
    if (!ch || !/^[\u4e00-\u9fff]$/.test(ch) || !jyut) {
      continue;
    }
    const bucket = rowsByChar.get(ch) ?? [];
    bucket.push({ rank: rankValue(pronRank), jyut });
    rowsByChar.set(ch, bucket);
  }
  const out: RimeEntry[] = [];
  for (const rows of rowsByChar.values()) {
    const preset = rows.filter((r) => r.rank === 0);
    const minRank = Math.min(...rows.map((r) => r.rank));
    const pickFrom = preset.length ? preset : rows.filter((r) => r.rank === minRank);
    for (const row of pickFrom) {
      out.push(...tokensToRimeEntries(row.jyut));
    }
  }
  return out;
}

function collectFragmentCandidates(entries: RimeEntry[]): Set<string> {
  const candidates = new Set<string>([...VOWEL_RHYME_LETTERS, 'm', 'ng']);
  for (const { letters } of entries) {
    candidates.add(letters);
    for (let len = 1; len <= letters.length; len++) {
      candidates.add(letters.slice(-len));
    }
  }
  return candidates;
}

function buildFinalOptions(entries: RimeEntry[], candidates: Set<string>): Record<string, string[]> {
  const out: Record<string, Set<string>> = {};
  for (const fragment of candidates) {
    const norm = normalizeRhymeLetters(fragment);
    const finals = new Set<string>();
    for (const entry of entries) {
      if (!syllableMatchesRhymeFragment(entry.letters, fragment)) {
        continue;
      }
      if (isStandaloneNasalSyllableToken(entry.token)) {
        for (const n of STANDALONE_NASAL_FINALS) {
          finals.add(n);
        }
        continue;
      }
      if (entry.final) {
        finals.add(entry.final);
      }
    }
    if (finals.size) {
      out[norm] = finals;
    }
  }
  const sorted: Record<string, string[]> = {};
  for (const [k, set] of Object.entries(out)) {
    sorted[k] = [...set].sort();
  }
  return sorted;
}

/** Port of jyutping_anchor.default_syllable_letters_for_anchor_char — preset 單字音節字母 */
export function buildAnchorCharLetters(repoRoot: string): Record<string, string> {
  const csvPath = path.join(path.resolve(repoRoot), 'data/rime/char.csv');
  if (!fs.existsSync(csvPath)) {
    return {};
  }
  const lines = fs.readFileSync(csvPath, 'utf8').split(/\r?\n/);
  if (!lines.length) {
    return {};
  }
  const header = lines[0]!.split(',');
  const charIdx = header.indexOf('char');
  const jyutIdx = header.indexOf('jyutping');
  const rankIdx = header.indexOf('pron_rank');
  if (jyutIdx < 0) {
    return {};
  }
  const rowsByChar = new Map<string, Array<{ rank: number; jyut: string }>>();
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]!.trim();
    if (!line) {
      continue;
    }
    const cols = line.split(',');
    const ch = (cols[charIdx] ?? '').trim();
    const jyut = (cols[jyutIdx] ?? '').trim();
    const pronRank = rankIdx >= 0 ? (cols[rankIdx] ?? '').trim() : '預設';
    if (!ch || !/^[\u4e00-\u9fff]$/.test(ch) || !jyut) {
      continue;
    }
    const bucket = rowsByChar.get(ch) ?? [];
    bucket.push({ rank: rankValue(pronRank), jyut });
    rowsByChar.set(ch, bucket);
  }
  const out: Record<string, string> = {};
  for (const [ch, rows] of rowsByChar) {
    const preset = rows.filter((r) => r.rank === 0);
    const minRank = Math.min(...rows.map((r) => r.rank));
    const pickFrom = preset.length ? preset : rows.filter((r) => r.rank === minRank);
    const token = pickFrom[0]?.jyut.split(/\s+/)[0] ?? '';
    const letters = syllableLetters(token);
    if (letters) {
      out[ch] = letters;
    }
  }
  return out;
}

export function buildRhymeLetterIndex(repoRoot: string): {
  finalOptions: Record<string, string[]>;
  completeSyllables: string[];
  anchorCharLetters: Record<string, string>;
} {
  const csvPath = path.join(path.resolve(repoRoot), 'data/rime/char.csv');
  if (!fs.existsSync(csvPath)) {
    return { finalOptions: {}, completeSyllables: [], anchorCharLetters: {} };
  }
  const entries = parseCharCsvEntries(fs.readFileSync(csvPath, 'utf8'));
  const completeSyllables = [...new Set(entries.map((e) => e.letters))].sort();
  const candidates = collectFragmentCandidates(entries);
  const finalOptions = buildFinalOptions(entries, candidates);
  const anchorCharLetters = buildAnchorCharLetters(repoRoot);
  return { finalOptions, completeSyllables, anchorCharLetters };
}

export function loadRhymeLetterData(repoRoot: string): void {
  initRhymeLetterIndex(buildRhymeLetterIndex(repoRoot));
}
