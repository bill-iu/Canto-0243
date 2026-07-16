/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PORTABLE_HOST?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
