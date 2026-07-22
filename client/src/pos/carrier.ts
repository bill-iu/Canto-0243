/**
 * 詞性載體 runtime — independent of lyrics.db (ADR-0058).
 * Missing / failed load → 詞性缺標 (no throw, no gate block).
 * 閘用詞類 = entry.gate (high|medium); 展示 = entry.show (high only).
 */
import type { FormalPos, PosCode, PosEntry, ProjectPosCarrier } from './types.ts';
import { FAMILY_LABEL_ZH, FORMAL_POS, POS_LABEL_ZH, VOICE_LABEL_ZH } from './types.ts';

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

function formalCodes(codes: readonly string[] | undefined): Set<string> {
  const out = new Set<string>();
  for (const p of codes ?? []) {
    if (FORMAL_POS.has(p)) out.add(p);
  }
  return out;
}

/** 閘用詞類 for workbench filter / campaign same-pos. */
export function formalPosOf(literal: string): ReadonlySet<string> {
  const e = getPosEntry(literal);
  if (!e) return new Set();
  if (e.gate != null) return formalCodes(e.gate);
  if (e.trust === 'low') return new Set();
  if (e.trust === 'high' || e.trust === 'medium') return formalCodes(e.pos);
  // legacy carrier without trust/gate: use raw formal pos
  return formalCodes(e.pos);
}

export function formalPosMap(): ReadonlyMap<string, ReadonlySet<string>> {
  const map = new Map<string, ReadonlySet<string>>();
  if (!carrier) return map;
  for (const lit of Object.keys(carrier.literals)) {
    const formal = formalPosOf(lit);
    if (formal.size) map.set(lit, formal);
  }
  return map;
}

/**
 * Formal pos codes for creator filter + detail chips: show ∪ pos (any trust).
 * Grill 2026-07-21 C — cow-single/low (e.g. 金錢) participates; no 「未審」 label.
 */
export function creatorFormalPosCodes(entry: PosEntry | null | undefined): FormalPos[] {
  if (!entry) return [];
  const out: FormalPos[] = [];
  const seen = new Set<string>();
  for (const p of [...(entry.show ?? []), ...entry.pos]) {
    if (p === 'u' || !FORMAL_POS.has(p) || seen.has(p)) continue;
    seen.add(p);
    out.push(p as FormalPos);
  }
  return out;
}

/** Creator-facing chips (formal pos + family/voice); omit section when empty. */
export function posDisplayChips(literal: string): string[] {
  const e = getPosEntry(literal);
  if (!e) return [];
  const chips: string[] = [];
  for (const p of creatorFormalPosCodes(e)) {
    const label = POS_LABEL_ZH[p as PosCode];
    if (label) chips.push(label);
  }
  if (e.family) chips.push(FAMILY_LABEL_ZH[e.family]);
  if (e.voice) chips.push(VOICE_LABEL_ZH[e.voice]);
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
