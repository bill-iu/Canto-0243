/** ponytail: DB-4 — SW urlPattern must match dev + release semver lexicon URLs */
const pattern = /\/lyrics\.(?:dev|v?\d+\.\d+\.\d+)\.db$/;

for (const url of ['/lyrics.dev.db', '/lyrics.v1.2.3.db', '/Canto-0243/lyrics.dev.db']) {
  if (!pattern.test(url)) {
    throw new Error(`lexicon-restore-self-check: expected match ${url}`);
  }
}
for (const url of ['/lyrics.db', '/lyrics.latest.db']) {
  if (pattern.test(url)) {
    throw new Error(`lexicon-restore-self-check: expected miss ${url}`);
  }
}

console.log('lexicon-restore self-check ok');
