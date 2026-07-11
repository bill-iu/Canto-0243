/** Search-mode behaviour contract shared by Portable and PWA. */
export const CODE_PROFILES = Object.freeze(['m1', 'm2', 'm3']);
export const SEARCH_FAMILIES = Object.freeze(['basic', 'pingze', 'synonym']);

export function isCodeProfile(value) {
  return CODE_PROFILES.includes(value);
}

export function uiModeToUrlMode(mode) {
  return mode === '02493' ? 'm2' : mode === '394052' ? 'm3' : mode === 'synonym' ? 'syn' : mode === 'pingze' ? 'pz' : 'm1';
}

export function urlModeToUiMode(mode) {
  return mode === 'm2' ? '02493' : mode === 'm3' ? '394052' : mode === 'syn' ? 'synonym' : mode === 'pz' ? 'pingze' : '0243';
}

export function uiModeToProfile(mode) {
  return uiModeToUrlMode(mode) === 'm2' ? 'm2' : uiModeToUrlMode(mode) === 'm3' ? 'm3' : 'm1';
}

export function profileToUiMode(profile) {
  return urlModeToUiMode(isCodeProfile(profile) ? profile : 'm1');
}

export function searchFamilyForUiMode(mode) {
  return mode === 'pingze' ? 'pingze' : mode === 'synonym' ? 'synonym' : 'basic';
}
