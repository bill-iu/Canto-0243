/** ponytail: DB-4 + ADR-0032 G — SW urlPattern must match dev + release lexicon URLs (plain + gzip) */
const pattern = /\/lyrics(?:\.[^/]+)?\.db(?:\.gz)?$/;

for (const url of [
  '/lyrics.dev.db',
  '/lyrics.v1.2.3.db',
  '/Canto-0243/lyrics.dev.db',
  '/lyrics.394052.db.gz',
  '/Canto-0243/lyrics.394052.db.gz',
]) {
  if (!pattern.test(url)) {
    throw new Error(`lexicon-restore-self-check: expected match ${url}`);
  }
}
for (const url of ['/lexicon-manifest.json', '/fonts/fonts.css', '/index.html']) {
  if (pattern.test(url)) {
    throw new Error(`lexicon-restore-self-check: expected miss ${url}`);
  }
}

console.log('lexicon-restore self-check ok');
