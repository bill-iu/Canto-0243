/** ponytail: ranking sort self-check for P3 */
import { rankingLogicSelfCheck } from '../src/db/ranking.ts';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildRankingData, loadRankingData, parseWordPronRanks } from '../src/db/ranking-loader.node.ts';
import { compareAuthoritativeReadings, compareSearchResults, pronRankSortValueForWord } from '../src/db/ranking.ts';

rankingLogicSelfCheck();
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
loadRankingData(root);
const originalCharGrade = pronRankSortValueForWord('會', 'wui2');
assert.equal(pronRankSortValueForWord('社會保障', 'se5 wui2 bou2 zoeng3'), 0);
assert.equal(pronRankSortValueForWord('從容應對', 'sung1 jung4 jing3 deoi3'), 1);
assert.equal(pronRankSortValueForWord('利潤率', 'lei6 jeon6 leot6'), 1);
assert.equal(pronRankSortValueForWord('無縫', 'mou4 fung6'), 1);
assert.equal(pronRankSortValueForWord('聽不見', 'ting1 bat1 gin3'), 2);
assert.equal(pronRankSortValueForWord('衝着', 'cung3 zoek6'), 3);
assert.equal(pronRankSortValueForWord('社會', 'se5 wui2'), Math.max(
  pronRankSortValueForWord('社', 'se5'), originalCharGrade,
)); // unlisted word keeps character fallback
assert.equal(pronRankSortValueForWord('會', 'wui2'), originalCharGrade);
for (const char of ['弱勢社群', '弱勢社羣']) {
  assert.equal(pronRankSortValueForWord(char, 'joek6 sai3 se5 kwan4'), 0);
}
for (const [char, preferred, variant] of [
  ['長於', 'zoeng2 jyu1', 'coeng4 jyu1'],
  ['首尾相連', 'sau2 mei5 soeng1 lin4', 'sau2 mei2 soeng1 lin4'],
  ['鈾礦', 'jau2 kwong3', 'jau4 kwong3'],
  ['烷基', 'jyun2 gei1', 'jyun4 gei1'],
]) {
  const rows = [{ char: char!, jyutping: variant! }, { char: char!, jyutping: preferred! }];
  for (const compare of [compareSearchResults, compareAuthoritativeReadings]) {
    assert.equal([...rows].sort(compare)[0]!.jyutping, preferred);
  }
}
const valid = { char: '群山', ingested_char: '羣山', jyutping: 'kwan4 saan1', pron_rank: '預設' };
for (const invalid of [null, {}, [null], [{ ...valid, pron_rank: 'constructor' }],
  [{ ...valid, pron_rank: ['預設'] }], [{ ...valid, char: '群' }], [{ ...valid, jyutping: 'kwan7 saan1' }],
  [valid, { ...valid, char: '羣山', pron_rank: '常用' }]]) {
  assert.throws(() => parseWordPronRanks(JSON.stringify(invalid)));
}
assert.equal(buildRankingData(root).pronRank['長於\tzoeng2 jyu1'], 0);
console.log('ranking self-check ok');
