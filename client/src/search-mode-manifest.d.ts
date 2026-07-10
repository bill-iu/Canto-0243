declare module '../../contracts/search-mode-manifest.mjs' {
  export function uiModeToUrlMode(mode: string): string;
  export function urlModeToUiMode(mode: string): string;
  export function uiModeToProfile(mode: string): 'm1' | 'm2' | 'm3';
  export function profileToUiMode(profile: string): string;
  export function searchFamilyForUiMode(mode: string): 'basic' | 'pingze' | 'synonym';
}
