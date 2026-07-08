export const PWA_GATE_LANDED_KEY = 'canto-pwa-gate-landed';

export function hasPwaGateLanded(): boolean {
  try {
    return Boolean(sessionStorage.getItem(PWA_GATE_LANDED_KEY));
  } catch {
    return false;
  }
}

export function revealPwaShell(): void {
  document.documentElement.classList.add('pwa-shell-revealed');
  document.getElementById('pwaBootGate')?.remove();
}

export function applyBootThemeFromStorage(): void {
  try {
    const theme = localStorage.getItem('canto-theme');
    if (theme === 'dark' || theme === 'light') {
      document.documentElement.dataset.theme = theme;
    }
  } catch {
    /* storage unavailable */
  }
}