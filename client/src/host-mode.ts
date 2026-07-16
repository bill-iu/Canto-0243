/** Build-time portable host (FastAPI + /words/search). PWA builds leave this false. */
export function isPortableHost(): boolean {
  return import.meta.env.VITE_PORTABLE_HOST === '1';
}
