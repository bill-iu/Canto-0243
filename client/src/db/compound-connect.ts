/**
 * 連接詞複合（~與~／!與!）— ADR-0053：詞庫 ∪ 合成 + syn/ant 互斥。
 * Port of app/domain/relations/compound_connect.py
 */
import type { Database } from './sqljs.ts';
import { queryRows } from './database-backend.ts';
import { ensureConnectiveCompoundRows, ensureComposedWordRow } from './db-patch.ts';
import { FILLWORD_CONNECTIVES_SET as FILLWORD_CONNECTIVES } from './_generated/fillword-connectives.ts';

export type ConnectiveCompoundKind = 'syn' | 'ant';

/** Lexicon hits keep flank tier 0–2; synthetic always ranks after. */
export const TIER_CONNECTIVE_SYNTH = 3;

/** Grill: cap synth so first !與! / ~與~ does not freeze main thread. */
export const CONNECTIVE_SYNTH_CAP = 500;
const SYNTH_YIELD_EVERY = 25;

type TierMap = Map<string, number>;

function yieldToMain(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function flankTiersFromTwoChar(twoCharTiers: TierMap): Map<string, number> {
  const out = new Map<string, number>();
  for (const [w, tier] of twoCharTiers) {
    if (w.length !== 2) continue;
    for (const pair of [`${w[0]}\t${w[1]}`, `${w[1]}\t${w[0]}`]) {
      const prev = out.get(pair);
      out.set(pair, prev === undefined ? tier : Math.min(prev, tier));
    }
  }
  return out;
}

/**
 * Strict mutual exclusion with ant-wins:
 * - syn path: drop any pair also on ant (反義唔入 ~)
 * - ant path: keep full ant primary (近義污染唔踢走 !! 對)
 */
export function exclusiveTwoCharTiers(
  primary: TierMap,
  opposite: TierMap,
  kind: ConnectiveCompoundKind,
): TierMap {
  if (kind === 'ant') {
    return new Map(primary);
  }
  const out = new Map<string, number>();
  for (const [w, tier] of primary) {
    if (!opposite.has(w)) {
      out.set(w, tier);
    }
  }
  return out;
}

async function loadThreeCharLiterals(db: Database): Promise<Set<string>> {
  const rows = await queryRows(
    db,
    `
    SELECT DISTINCT char FROM words
    WHERE length = 3 OR ((length IS NULL OR length = 0) AND length(char) = 3)
  `,
  );
  const out = new Set<string>();
  for (const row of rows) {
    const ch = String(row.char ?? '');
    if (ch.length === 3) out.add(ch);
  }
  return out;
}

/** Cache key → tiers; cleared via resetConnectiveCompoundCache. */
const connectiveTierCache = new Map<string, TierMap>();

export function resetConnectiveCompoundCache(): void {
  connectiveTierCache.clear();
}

/**
 * ~{連}~／!{連}!：詞庫三字 ∩ exclusive flank，再合成缺席 A連B。
 */
export async function searchConnectiveCompoundTiers(
  db: Database,
  opts: {
    compoundKind: ConnectiveCompoundKind;
    connective: string;
    synTiers: TierMap;
    antTiers: TierMap;
  },
): Promise<TierMap> {
  const { compoundKind, connective, synTiers, antTiers } = opts;
  if (!connective || !FILLWORD_CONNECTIVES.has(connective)) {
    return new Map();
  }

  const cacheKey = `${compoundKind}\0${connective}\0${synTiers.size}\0${antTiers.size}`;
  const cached = connectiveTierCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  await ensureConnectiveCompoundRows(db);

  const primary = compoundKind === 'ant' ? antTiers : synTiers;
  const opposite = compoundKind === 'ant' ? synTiers : antTiers;
  const exclusive = exclusiveTwoCharTiers(primary, opposite, compoundKind);
  const flankTiers = flankTiersFromTwoChar(exclusive);
  if (!flankTiers.size) {
    const empty = new Map<string, number>();
    connectiveTierCache.set(cacheKey, empty);
    return empty;
  }

  const tiers = new Map<string, number>();
  for (const w of await loadThreeCharLiterals(db)) {
    if (w[1] !== connective) continue;
    const tier = flankTiers.get(`${w[0]}\t${w[2]}`);
    if (tier !== undefined) {
      tiers.set(w, tier);
    }
  }

  // Lexicon hits first (already in `tiers`); synth up to CAP with main-thread yields
  const pending: string[] = [];
  for (const [pair] of flankTiers) {
    if (pending.length >= CONNECTIVE_SYNTH_CAP) break;
    const tab = pair.indexOf('\t');
    if (tab < 0) continue;
    const a = pair.slice(0, tab);
    const b = pair.slice(tab + 1);
    if (!a || !b) continue;
    const compound = `${a}${connective}${b}`;
    if (!tiers.has(compound)) {
      pending.push(compound);
    }
  }
  let n = 0;
  for (const compound of pending) {
    const ok = await ensureComposedWordRow(db, compound);
    if (ok) {
      tiers.set(compound, TIER_CONNECTIVE_SYNTH);
    }
    n += 1;
    if (n % SYNTH_YIELD_EVERY === 0) {
      await yieldToMain();
    }
  }

  connectiveTierCache.set(cacheKey, tiers);
  return tiers;
}
