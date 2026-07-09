/**
 * Open-time phoneme storage contract (ADR-0037/0038 C1).
 * PWA does not migrate in-browser; purge channel caches and re-download.
 */
import type { DatabaseBackend } from './database-backend.ts';
import { queryFirst, queryRows } from './database-backend.ts';
import { PHONEME_VOCAB_VERSION } from './phoneme-codec.ts';

const META_VERSION_KEY = 'phoneme_vocab_version';

function looksLikeJsonArray(raw: unknown): boolean {
  return typeof raw === 'string' && raw.trim().startsWith('[');
}

export async function phonemeStorageContractOk(db: DatabaseBackend): Promise<boolean> {
  let version: string | null = null;
  try {
    const row = await queryFirst(
      db,
      'SELECT value FROM lexicon_meta WHERE key = ? LIMIT 1',
      [META_VERSION_KEY],
    );
    if (row && row.value != null) {
      version = String(row.value);
    }
  } catch {
    version = null;
  }
  if (version !== PHONEME_VOCAB_VERSION) {
    return false;
  }
  try {
    const samples = await queryRows(
      db,
      `SELECT finals, initials FROM words
       WHERE (finals IS NOT NULL AND finals != '')
          OR (initials IS NOT NULL AND initials != '')
       LIMIT 20`,
      [],
    );
    for (const row of samples) {
      if (looksLikeJsonArray(row.finals) || looksLikeJsonArray(row.initials)) {
        return false;
      }
    }
  } catch {
    return false;
  }
  return true;
}

export async function assertPhonemeStorageContract(
  db: DatabaseBackend,
  onFail?: () => Promise<void>,
): Promise<void> {
  if (await phonemeStorageContractOk(db)) {
    return;
  }
  if (onFail) {
    await onFail();
  }
  throw new Error(
    '詞庫音素欄位契約不符（需要 j2 compact + lexicon_meta）。' +
      '已嘗試清本地詞庫快取；請重新載入以下載新渠道包。' +
      '本機 Python：python -m ingest.migrate_phoneme_compact lyrics.db',
  );
}
