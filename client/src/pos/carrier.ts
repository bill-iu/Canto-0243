/**
 * 詞性載體 runtime — independent of lyrics.db (ADR-0058).
 * Missing / failed load → 詞性缺標 (no throw, no gate block).
 */
import type { PosCode, PosEntry, ProjectPosCarrier } from './types.ts';
import { FORMAL_POS } from './types.ts';

let carrier: ProjectPosCarrier | null = null;
let loadAttempted = false;

export function isProjectPosReady(): boolean {
  return carrier != null;
}

export function getProjectPosVersion(): string | null {
  return carrier?.version ?? null;
}

export function isP0HardGate(): boolean {
  return Boolean(carrier?.p0HardGate);
}

export function getPosEntry(literal: string): PosEntry | null {
  if (!carrier) return null;
  const e = carrier.literals[literal.trim()];
  return e ?? null;
}

export function formalPosOf(literal: string): ReadonlySet<string> {
  const e = getPosEntry(literal);
  if (!e) return new Set();
  return new Set(e.pos.filter((p) => FORMAL_POS.has(p)));
}

export function formalPosMap(): ReadonlyMap<string, ReadonlySet<string>> {
  const map = new Map<string, ReadonlySet<string>>();
  if (!carrier) return map;
  for (const [lit, entry] of Object.entries(carrier.literals)) {
    const formal = new Set(entry.pos.filter((p) => FORMAL_POS.has(p)));
    if (formal.size) map.set(lit, formal);
  }
  return map;
}

/** Creator-facing chips; omit 未定. */
export function posDisplayChips(literal: string): string[] {
  const e = getPosEntry(literal);
  if (!e) return [];
  const chips: string[] = [];
  for (const p of e.pos) {
    if (p === 'u') continue;
    const label = ({ n: '名', v: '動', a: '形', r: '副', x: '虛' } as Record<PosCode, string>)[p];
    if (label) chips.push(label);
  }
  if (e.family === 'idiom') chips.push('熟語');
  if (e.voice === 'active') chips.push('主動');
  if (e.voice === 'passive') chips.push('被動');
  return chips;
}

export function initProjectPosCarrier(data: ProjectPosCarrier | null | undefined): void {
  if (!data || typeof data !== 'object' || !data.literals) {
    carrier = null;
    return;
  }
  carrier = {
    version: String(data.version || '0'),
    p0HardGate: Boolean(data.p0HardGate),
    literals: data.literals,
  };
}

export function resetProjectPosCarrier(): void {
  carrier = null;
  loadAttempted = false;
}

/** Fetch once; safe no-op on failure. */
export async function ensureProjectPosCarrier(fetchUrl: string): Promise<void> {
  if (loadAttempted) return;
  loadAttempted = true;
  try {
    const res = await fetch(fetchUrl);
    if (!res.ok) return;
    initProjectPosCarrier((await res.json()) as ProjectPosCarrier);
  } catch {
    /* 詞性缺標 */
  }
}
