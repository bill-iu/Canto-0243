/**
 * ponytail: 音節拼接須揀 rime 預設，唔取 DB 插入序（棄用 cung1 先於預設 cung4）。
 * Run: npx tsx client/scripts/compose-default-reading-self-check.ts
 */
import { pickComposeSingleCharReading } from '../src/db/db-patch.ts';
import { initRankingData } from '../src/db/ranking.ts';

initRankingData({
  pronRank: {
    '從\tcung1': 3, // 棄用
    '從\tcung4': 0, // 預設
    '從\tsung1': 2, // 罕見
  },
});

const picked = pickComposeSingleCharReading('從', [
  { jyutping: 'cung1', code: '3' },
  { jyutping: 'cung4', code: '0' },
  { jyutping: 'sung1', code: '3' },
]);

if (!picked || picked.jyutping !== 'cung4' || picked.code !== '0') {
  console.error('compose-default-reading-self-check: expected cung4/0, got', picked);
  process.exit(1);
}

console.log('compose-default-reading-self-check: ok');
