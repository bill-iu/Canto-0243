/**
 * DB-2 runnable self-check — run in browser (poc page or ?selfcheck=1).
 */
import {
  ensureLexiconInOpfs,
  readLexiconFromOpfs,
  removeLexiconFromOpfs,
} from './opfs-lexicon.ts';

const SQLITE_MAGIC = 'SQLite format 3\u0000';

export async function opfsLexiconSelfCheck(
  fetchFixture: () => Promise<Uint8Array>,
  version = 'selfcheck',
): Promise<void> {
  await removeLexiconFromOpfs(version);

  let fetches = 0;
  const fetchOnce = async () => {
    fetches += 1;
    return fetchFixture();
  };

  const first = await ensureLexiconInOpfs({ version, fetchBytes: fetchOnce });
  if (!first.fetched || fetches !== 1) {
    throw new Error(`opfsLexiconSelfCheck: first ensure should fetch once (fetches=${fetches})`);
  }

  const second = await ensureLexiconInOpfs({ version, fetchBytes: fetchOnce });
  if (second.fetched || fetches !== 1) {
    throw new Error(`opfsLexiconSelfCheck: second ensure must not fetch (fetches=${fetches})`);
  }
  if (second.byteSize !== first.byteSize) {
    throw new Error('opfsLexiconSelfCheck: byteSize mismatch on cache hit');
  }

  const fromOpfs = await readLexiconFromOpfs(version);
  if (!fromOpfs?.byteLength || fromOpfs.byteLength !== first.byteSize) {
    throw new Error('opfsLexiconSelfCheck: readLexiconFromOpfs size mismatch');
  }

  const head = new TextDecoder().decode(fromOpfs.slice(0, 16));
  if (!head.startsWith(SQLITE_MAGIC)) {
    throw new Error('opfsLexiconSelfCheck: OPFS payload is not SQLite');
  }

  await removeLexiconFromOpfs(version);
}
