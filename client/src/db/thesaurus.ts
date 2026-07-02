/**
 * Static thesaurus syn index (browser / Node) — port of get_synonyms subset.
 * ponytail: syn only; ant deferred until relation pool needs it
 */

let staticSyn: Record<string, string[]> = {};
let staticAnt: Record<string, string[]> = {};
let staticCilinSyn: Record<string, string[]> = {};

export function initStaticSynIndex(data: Record<string, string[]>): void {
  staticSyn = data ?? {};
}

export function initStaticAntIndex(data: Record<string, string[]>): void {
  staticAnt = data ?? {};
}

export function initStaticCilinSynIndex(data: Record<string, string[]>): void {
  staticCilinSyn = data ?? {};
}

export function initStaticRelationIndex(data: {
  syn?: Record<string, string[]>;
  ant?: Record<string, string[]>;
  cilin?: Record<string, string[]>;
}): void {
  if (data.syn) {
    staticSyn = data.syn;
  }
  if (data.ant) {
    staticAnt = data.ant;
  }
  if (data.cilin) {
    staticCilinSyn = data.cilin;
  }
}

export function getStaticSynonyms(char: string): string[] {
  if (!char) {
    return [];
  }
  return staticSyn[char] ?? [];
}

export function getStaticAntonyms(char: string): string[] {
  if (!char) {
    return [];
  }
  return (staticAnt[char] ?? []).slice(0, 12);
}

export function getCilinSynonyms(char: string): string[] {
  if (!char) {
    return [];
  }
  return staticCilinSyn[char] ?? [];
}

export function resetStaticSynIndex(): void {
  staticSyn = {};
  staticAnt = {};
  staticCilinSyn = {};
}
