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
  return (import.meta as ImportMeta).env?.VITE_LEXICON_VERSION || 'v1.0.7';
}

export function publicAssetUrl(file: string): string {
  const base = (import.meta as ImportMeta).env?.BASE_URL || '/';
  return `${base.replace(/\/?$/, '/')}${file.replace(/^\//, '')}`;
}

export function supportsGzipDecompression(): boolean {
  return typeof DecompressionStream !== 'undefined';
}

function isViteDev(): boolean {
  return typeof import.meta !== 'undefined' && Boolean((import.meta as ImportMeta).env?.DEV);
}

function fallbackTarget(version: string): LexiconTarget {
  // plain lyrics.db; version lives in manifest / OPFS key (ADR-0035 era naming)
  const dbUrl = publicAssetUrl('lyrics.db');
  return { version, dbUrl, fetchUrl: dbUrl, useGzip: false };
}

/**
 * DEV：只認目前掛載嘅 lyrics.db（vite 優先根 SSOT），唔用 manifest 做 size／sha 閘。
 * OPFS key 帶 live byteSize，換庫會自動 miss cache。
 */
export function buildDevLexiconTarget(version: string, liveByteSize?: number): LexiconTarget {
  const dbUrl = publicAssetUrl('lyrics.db');
  return {
    version: liveByteSize != null ? `${version}-dev-${liveByteSize}` : `${version}-dev`,
    dbUrl,
    fetchUrl: dbUrl,
    useGzip: false,
  };
}

export function resolveTargetFromManifest(manifest: LexiconManifest, version: string): LexiconTarget {
  if (!manifest.lexiconVersion || !manifest.dbFile) {
    return fallbackTarget(version);
  }
  const dbUrl = publicAssetUrl(manifest.dbFile);
  // DEV 正式入口係 loadLexiconTarget；呢度唔綁 stale manifest 完整性欄
  if (isViteDev()) {
    return buildDevLexiconTarget(manifest.lexiconVersion || version);
  }
  const canGzip = Boolean(
    manifest.preferCompressed && manifest.dbFileGz && supportsGzipDecompression(),
  );
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
  if (isViteDev()) {
    const dbUrl = publicAssetUrl('lyrics.db');
    let liveSize: number | undefined;
    try {
      const head = await fetch(dbUrl, { method: 'HEAD', cache: 'no-cache' });
      const len = head.headers.get('content-length');
      if (len && Number.isFinite(Number(len))) liveSize = Number(len);
    } catch {
      /* HEAD 失敗仍可開庫；version 無 size 後綴 */
    }
    return buildDevLexiconTarget(version, liveSize);
  }
  try {
    const res = await fetch(publicAssetUrl('lexicon-manifest.json'), { cache: 'no-cache' });
    if (!res.ok) return fallbackTarget(version);
    const manifest = (await res.json()) as LexiconManifest;
    return resolveTargetFromManifest(manifest, version);
  } catch {
    return fallbackTarget(version);
  }
}
