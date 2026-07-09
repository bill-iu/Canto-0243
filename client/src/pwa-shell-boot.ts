export const PWA_GATE_LANDED_KEY = 'canto-pwa-gate-landed';

export function hasPwaGateLanded(): boolean {
  try {
    return Boolean(sessionStorage.getItem(PWA_GATE_LANDED_KEY));
  } catch {
    return false;
  }
}

/** 就緒閘解鎖後露出 App shell（與 Portable gate.mjs 共用 class `shell-revealed`） */
export function revealPwaShell(): void {
  document.documentElement.classList.add('shell-revealed');
  document.getElementById('pwaBootGate')?.remove();
}

export function applyBootThemeFromStorage(): void {
  try {
    const theme = localStorage.getItem('canto-theme');
    document.documentElement.dataset.theme =
      theme === 'dark' || theme === 'light' ? theme : 'dark';
  } catch {
    document.documentElement.dataset.theme = 'dark';
  }
}