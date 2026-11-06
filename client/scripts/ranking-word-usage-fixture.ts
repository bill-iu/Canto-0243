import assert from 'node:assert/strict';
import { initSqlJs } from '../src/db/sqljs.ts';
import { createSqlJsBackend } from '../src/db/sqljs-backend.ts';
import { finalizeCanonicalMatchSpec } from '../src/db/position-match/canonical.ts';
import { executeCanonicalMatchSpecPage } from '../src/db/position-match/engine.ts';
import { compareAuthoritativeReadings, compareHeteronym, compareSearchResults, initRankingData } from '../src/db/ranking.ts';
import { loadRankingData, parseWordUsage } from '../src/db/ranking-loader.node.ts';

export async function checkWordUsageRanking(root: string): Promise<void> {
  const header = 'char\tusage_rank\tsubtitle_channels\taction\n';
  for (const invalid of ['bad', `${header}詞\t4\t0\tkeep`, `${header}詞\t1\t-1\tkeep`,
    `${header}詞\t3\t0\tkeep`, `${header}詞\t1\t0\twithdraw_curated`,
    `${header}詞\t1\t0\tkeep\n詞\t2\t0\tkeep`]) {
    assert.throws(() => parseWordUsage(invalid));
  }
  assert.deepEqual(parseWordUsage(`${header}__proto__\t1\t0\tkeep`).__proto__, [1, 0]);
  const cold = Array.from({ length: 205 }, (_, index) => `古語甲${String.fromCodePoint(0x4e00+index)}`);
  const common = '事發經過';
  const wordUsage: Record<string, readonly [number, number]> = Object.fromEntries(cold.map(char => [char, [2, 0] as const]));
  wordUsage[common] = [0, 0];
  initRankingData({
    essay: Object.fromEntries(cold.map(char => [char, 5000])),
    curated: [], wordUsage,
    pronRank: { [`${common}\tsi6 faat3 ging1 gwo3`]: 0, [`${common}\tsi6 faat3 ging1 gwo2`]: 1 },
  });
  const SQL = await initSqlJs();
  const native = new SQL.Database();
  native.run('CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, jyutping TEXT, code TEXT, initials TEXT, finals TEXT, length INTEGER)');
  for (const char of [...cold, common]) {
    native.run('INSERT INTO words (char,jyutping,code,length) VALUES (?,?,?,?)', [char, 'si6 faat3 ging1 gwo3', '2434', 4]);
  }
  const db = createSqlJsBackend(native);
  try {
    for (const compare of [compareSearchResults, compareHeteronym]) {
      const tiers = ['H', '今匀*', '古語甲一'].map(char => ({ char, jyutping: '' }));
      assert.deepEqual(tiers.sort(compare).map(row => row.char), ['古語甲一', '今匀*', 'H']);
      const extension = ['X', '𠮷A'].map(char => ({ char, jyutping: '' }));
      assert.equal(extension.sort(compare)[0]!.char, '𠮷A');
    }
    const rows = [{ char: cold[0]!, jyutping: 'si6 faat3 ging1 gwo3' }, { char: common, jyutping: 'si6 faat3 ging1 gwo3' }];
    assert.equal([...rows].sort(compareSearchResults)[0]!.char, common);
    const readings = [{ char: common, jyutping: 'si6 faat3 ging1 gwo2' }, { char: common, jyutping: 'si6 faat3 ging1 gwo3' }];
    assert.equal(readings.sort(compareAuthoritativeReadings)[0]!.jyutping, 'si6 faat3 ging1 gwo3');
    const spec = finalizeCanonicalMatchSpec({ width: 4, slots: [], candidate_scope: 'complete' });
    for (const mode of ['m1', 'm2', 'm3']) {
      const first = await executeCanonicalMatchSpecPage(spec, { db, mode, limit: 200, offset: 0 });
      const second = await executeCanonicalMatchSpecPage(spec, { db, mode, limit: 200, offset: 200 });
      assert.equal(first.total, 206);
      assert.equal(first.rows[0]!.char, common, 'A common word inserted after 205 cold words must reach the first page');
      assert.equal(first.rows.length, 200);
      assert.equal(second.rows.length, 6);
      const seen = new Set(first.rows.map(row => row.char));
      assert(second.rows.every(row => !seen.has(row.char)));
    }
    initRankingData({
      essay: { 但係: 20000, 但是: 8720 }, curated: [], pronRank: {},
      wordUsage: { 但係: [0, 0], 但是: [0, 1255] },
    });
    assert.equal([
      { char: '但是', jyutping: 'daan6 si6' },
      { char: '但係', jyutping: 'daan6 hai6' },
    ].sort(compareSearchResults)[0]!.char, '但係', 'Subtitle coverage must not displace same-grade Cantonese Essay frequency');
  } finally {
    await db.close();
    loadRankingData(root);
  }
}
