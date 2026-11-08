/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_PORTABLE_HOST?: string;
  readonly VITE_RANKING_INDEX_SHA256?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'sql.js';
