/** lexicon-manifest.json → LexiconTarget（含壓縮傳輸 ADR-0032 G） */

export type LexiconManifest = {
  lexiconVersion?: string;
  dbFile?: string;
  dbFileGz?: string;
  byteSize?: number;
  compressedByteSize?: number;
  sha256?: string;
  preferCompressed?: boolean;
};

export type LexiconTarget = {
  version: string;
  /** plain `.db` — SW / offline cache key */
  dbUrl: string;
  /** actual download URL (may be `.db.gz`) */
  fetchUrl: string;
  byteSize?: number;
  sha256?: string;
  /** bytes expected on wire for progress */
  fetchByteSize?: number;
  useGzip: boolean;
};

export function lexiconVersionFromEnv(): string {
  return (import.meta as ImportMeta).env?.VITE_LEXICON_VERSION || 'dev';
}

export function publicAssetUrl(file: string): string {
  const base = (import.meta as ImportMeta).env?.BASE_URL || '/';
  return `${base.replace(/\/?$/, '/')}${file.replace(/^\//, '')}`;
}

export function supportsGzipDecompression(): boolean {
  return typeof DecompressionStream !== 'undefined';
}

function fallbackTarget(version: string): LexiconTarget {
  const dbFile = `lyrics.${version}.db`;
  const dbUrl = publicAssetUrl(dbFile);
  return { version, dbUrl, fetchUrl: dbUrl, useGzip: false };
}

export function resolveTargetFromManifest(manifest: LexiconManifest, version: string): LexiconTarget {
  if (!manifest.lexiconVersion || !manifest.dbFile) {
    return fallbackTarget(version);
  }
  const dbUrl = publicAssetUrl(manifest.dbFile);
  const devPlain =
    typeof import.meta !== 'undefined' && Boolean((import.meta as ImportMeta).env?.DEV);
  const canGzip =
    !devPlain &&
    Boolean(manifest.preferCompressed && manifest.dbFileGz && supportsGzipDecompression());
  if (!canGzip) {
    return {
      version: manifest.lexiconVersion,
      dbUrl,
      fetchUrl: dbUrl,
      byteSize: manifest.byteSize,
      sha256: manifest.sha256,
      fetchByteSize: manifest.byteSize,
      useGzip: false,
    };
  }
  const fetchUrl = publicAssetUrl(manifest.dbFileGz!);
  return {
    version: manifest.lexiconVersion,
    dbUrl,
    fetchUrl,
    byteSize: manifest.byteSize,
    sha256: manifest.sha256,
    fetchByteSize: manifest.compressedByteSize ?? manifest.byteSize,
    useGzip: true,
  };
}

export async function loadLexiconTarget(): Promise<LexiconTarget> {
  const version = lexiconVersionFromEnv();
  try {
    const res = await fetch(publicAssetUrl('lexicon-manifest.json'), { cache: 'no-cache' });
    if (!res.ok) return fallbackTarget(version);
    const manifest = (await res.json()) as LexiconManifest;
    return resolveTargetFromManifest(manifest, version);
  } catch {
    return fallbackTarget(version);
  }
}