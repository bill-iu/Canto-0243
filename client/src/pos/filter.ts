/** Creator-facing three-axis POS filter; display trust only. */
import { getPosEntry } from './carrier.ts';
import type { FormalPos, PosEntry, PosFamily, PosVoice } from './types.ts';

export type PosFilterState = {
  pos: FormalPos[];
  family: PosFamily[];
  voice: PosVoice[];
};

export const EMPTY_POS_FILTER: PosFilterState = { pos: [], family: [], voice: [] };

const POS_VALUES = new Set<FormalPos>(['n', 'v', 'a', 'r', 'x']);
const FAMILY_VALUES = new Set<PosFamily>(['idiom', 'chengyu', 'suyu', 'yanyu']);
const VOICE_VALUES = new Set<PosVoice>(['active', 'passive']);

function uniqueAllowed<T extends string>(values: readonly unknown[], allowed: ReadonlySet<T>): T[] {
  return [...new Set(values.filter((value): value is T => typeof value === 'string' && allowed.has(value as T)))];
}

export function normalizePosFilter(value: Partial<PosFilterState> | null | undefined): PosFilterState {
  const pos = uniqueAllowed(value?.pos ?? [], POS_VALUES);
  let family = uniqueAllowed(value?.family ?? [], FAMILY_VALUES);
  const voice = uniqueAllowed(value?.voice ?? [], VOICE_VALUES);
  if (family.includes('idiom')) family = ['idiom'];
  return { pos, family, voice };
}

export function posFilterActiveCount(value: PosFilterState): number {
  return value.pos.length + value.family.length + value.voice.length;
}

export function isPosFilterActive(value: PosFilterState): boolean {
  return posFilterActiveCount(value) > 0;
}

export function resetPosFilter(): PosFilterState {
  return { pos: [], family: [], voice: [] };
}

export function togglePosFilterValue<K extends keyof PosFilterState>(
  value: PosFilterState,
  axis: K,
  item: PosFilterState[K][number],
): PosFilterState {
  const current = value[axis] as string[];
  let next = current.includes(item) ? current.filter((entry) => entry !== item) : [...current, item];
  if (axis === 'family') {
    if (item === 'idiom' && !current.includes(item)) next = ['idiom'];
    else if (item !== 'idiom') next = next.filter((entry) => entry !== 'idiom');
  }
  return normalizePosFilter({ ...value, [axis]: next });
}

function intersects(a: readonly string[], b: readonly string[]): boolean {
  return a.some((value) => b.includes(value));
}

function familyMatches(entry: PosFamily | undefined, selected: readonly PosFamily[]): boolean {
  if (!selected.length) return true;
  if (!entry) return false;
  return selected.includes('idiom') ? true : selected.includes(entry);
}

export function posEntryMatchesFilter(entry: PosEntry | null, raw: PosFilterState): boolean {
  const filter = normalizePosFilter(raw);
  if (!isPosFilterActive(filter)) return true;
  if (!entry) return false;
  if (filter.pos.length && !intersects(entry.show ?? [], filter.pos)) return false;
  if (!familyMatches(entry.family, filter.family)) return false;
  if (filter.voice.length && (!entry.voice || !filter.voice.includes(entry.voice))) return false;
  return true;
}

export function literalMatchesPosFilter(literal: string, filter: PosFilterState): boolean {
  return posEntryMatchesFilter(getPosEntry(literal), filter);
}

export function filterByProjectPos<T>(
  rows: readonly T[],
  literalOf: (row: T) => string,
  filter: PosFilterState,
): T[] {
  if (!isPosFilterActive(filter)) return [...rows];
  return rows.filter((row) => literalMatchesPosFilter(literalOf(row), filter));
}
