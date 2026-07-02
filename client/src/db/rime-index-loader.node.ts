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

function parseCharCsvEntries(csvText: string): RimeEntry[] {
  const out: RimeEntry[] = [];
  const lines = csvText.split(/\r?\n/);
  if (!lines.length) {
    return out;
  }
  const header = lines[0]!.split(',');
  const charIdx = header.indexOf('char');
  const jyutIdx = header.indexOf('jyutping');
  const rankIdx = header.indexOf('pron_rank');
  if (jyutIdx < 0) {
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
    const pronRank = rankIdx >= 0 ? (cols[rankIdx] ?? '').trim() : '預設';
    if (!ch || !/^[\u4e00-\u9fff]$/.test(ch) || pronRank !== '預設' || !jyut) {
      continue;
    }
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
      out.push({ letters, final, token });
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

export function buildRhymeLetterIndex(repoRoot: string): {
  finalOptions: Record<string, string[]>;
  completeSyllables: string[];
} {
  const csvPath = path.join(path.resolve(repoRoot), 'data/rime/char.csv');
  if (!fs.existsSync(csvPath)) {
    return { finalOptions: {}, completeSyllables: [] };
  }
  const entries = parseCharCsvEntries(fs.readFileSync(csvPath, 'utf8'));
  const completeSyllables = [...new Set(entries.map((e) => e.letters))].sort();
  const candidates = collectFragmentCandidates(entries);
  const finalOptions = buildFinalOptions(entries, candidates);
  return { finalOptions, completeSyllables };
}

export function loadRhymeLetterData(repoRoot: string): void {
  initRhymeLetterIndex(buildRhymeLetterIndex(repoRoot));
}
