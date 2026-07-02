/**
 * Build static syn index from cilin + guotong (Node prebuild / parity runner).
 */
import fs from 'node:fs';
import path from 'node:path';

import { initStaticSynIndex, initStaticAntIndex } from './thesaurus.ts';

const CJK_RE = /[\u4e00-\u9fff]/;

function cleanTerm(text: string): string {
  return text
    .trim()
    .replace(/[（(].*?[）)]/g, '')
    .replace(/\s+/g, '');
}

function normalizeLiteral(text: string): string | null {
  const t = cleanTerm(text);
  if (!t || t.length > 12 || !CJK_RE.test(t) || /[0-9A-Za-z_]/.test(t)) {
    return null;
  }
  return t;
}

function literalTokens(parts: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of parts) {
    const t = normalizeLiteral(raw);
    if (t && !seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

function parseCilin(text: string): Record<string, string[]> {
  const groups: string[][] = [];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    const parts = trimmed.split(/\s+/);
    if (parts.length < 2) {
      continue;
    }
    const code = parts[0]!;
    if (!code.endsWith('=') || code.length < 8) {
      continue;
    }
    const words = literalTokens(parts.slice(1));
    if (words.length >= 2) {
      groups.push(words);
    }
  }

  const wordToGroups = new Map<string, string[][]>();
  for (const g of groups) {
    for (const w of g) {
      if (!w) {
        continue;
      }
      const list = wordToGroups.get(w) ?? [];
      list.push(g);
      wordToGroups.set(w, list);
    }
  }

  const out: Record<string, string[]> = {};
  for (const [w, gs] of wordToGroups) {
    const syns = new Set<string>();
    for (const g of gs) {
      for (const x of g) {
        if (x && x !== w) {
          syns.add(x);
        }
      }
    }
    if (syns.size) {
      out[w] = [...syns].sort();
    }
  }
  return out;
}

function parseGuotongSyn(text: string): Record<string, string[]> {
  const dict: Record<string, Set<string>> = {};
  for (const line of text.split(/\r?\n/)) {
    let trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    if (trimmed.includes('=')) {
      trimmed = trimmed.split('=', 2)[1]!;
    }
    const parts = trimmed
      .replace(/——/g, ' ')
      .replace(/—/g, ' ')
      .replace(/–/g, ' ')
      .split(/\s+/)
      .filter(Boolean);
    const words = literalTokens(parts);
    if (words.length < 2) {
      continue;
    }
    for (const w of words) {
      for (const other of words) {
        if (other !== w) {
          if (!dict[w]) {
            dict[w] = new Set();
          }
          dict[w]!.add(other);
        }
      }
    }
  }
  const out: Record<string, string[]> = {};
  for (const [k, set] of Object.entries(dict)) {
    out[k] = [...set].sort();
  }
  return out;
}

function mergeSynMaps(...maps: Array<Record<string, string[]>>): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const map of maps) {
    for (const [w, syns] of Object.entries(map)) {
      const set = new Set(out[w] ?? []);
      for (const s of syns) {
        if (s && s !== w) {
          set.add(s);
        }
      }
      if (set.size) {
        out[w] = [...set].sort();
      }
    }
  }
  return out;
}

function parseGuotongAnt(text: string): Record<string, string[]> {
  const dict: Record<string, Set<string>> = {};
  for (const line of text.split(/\r?\n/)) {
    let trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    if (trimmed.includes('=')) {
      trimmed = trimmed.split('=', 2)[1]!;
    }
    const parts = trimmed
      .replace(/——/g, ' ')
      .replace(/—/g, ' ')
      .replace(/–/g, ' ')
      .split(/\s+/)
      .filter(Boolean);
    const words = literalTokens(parts);
    if (words.length < 2) {
      continue;
    }
    for (const w of words) {
      for (const other of words) {
        if (other !== w) {
          if (!dict[w]) {
            dict[w] = new Set();
          }
          dict[w]!.add(other);
        }
      }
    }
  }
  const out: Record<string, string[]> = {};
  for (const [k, set] of Object.entries(dict)) {
    out[k] = [...set].sort();
  }
  return out;
}

export function buildStaticSynIndex(repoRoot: string): Record<string, string[]> {
  const root = path.resolve(repoRoot);
  const cilinPath = path.join(root, 'data/cilin/new_cilin.txt');
  const synPath = path.join(root, 'data/thesaurus/dict_synonym.txt');

  const maps: Array<Record<string, string[]>> = [];
  if (fs.existsSync(cilinPath)) {
    maps.push(parseCilin(fs.readFileSync(cilinPath, 'utf8')));
  }
  if (fs.existsSync(synPath)) {
    maps.push(parseGuotongSyn(fs.readFileSync(synPath, 'utf8')));
  }
  return maps.length ? mergeSynMaps(...maps) : {};
}

export function buildStaticAntIndex(repoRoot: string): Record<string, string[]> {
  const antPath = path.join(path.resolve(repoRoot), 'data/thesaurus/dict_antonym.txt');
  if (!fs.existsSync(antPath)) {
    return {};
  }
  return parseGuotongAnt(fs.readFileSync(antPath, 'utf8'));
}

export function loadStaticSynData(repoRoot: string): void {
  initStaticSynIndex(buildStaticSynIndex(repoRoot));
}

export function loadStaticRelationData(repoRoot: string): void {
  initStaticSynIndex(buildStaticSynIndex(repoRoot));
  initStaticAntIndex(buildStaticAntIndex(repoRoot));
}
