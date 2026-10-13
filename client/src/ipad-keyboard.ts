/** Best-effort input-session hygiene, NOT a Scribble/full-size-keyboard API. */
export function isIpadStandalone(
  nav: Pick<Navigator, 'userAgent' | 'platform' | 'maxTouchPoints'>,
  standalone: boolean,
): boolean {
  return standalone && (
    /iPad/.test(nav.userAgent) ||
    (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1)
  );
}

export type KeyboardRecoveryResult = 'ready' | 'composing' | 'unavailable';

/** Scope to the search field; never touch workbench drafts or restore focus on resume. */
export function bindIpadSearchKeyboardGuard(doc: Document, win: Window) {
  let composingTarget: EventTarget | null = null;
  const input = () => doc.querySelector<HTMLInputElement>('input#searchInput');
  const onCompositionStart = (event: Event) => {
    if (event.target === input()) composingTarget = event.target;
  };
  const onCompositionEnd = (event: Event) => {
    if (event.target === composingTarget) composingTarget = null;
  };

  const release = (): KeyboardRecoveryResult => {
    const field = input();
    if (!field || field.disabled || field.readOnly) return 'unavailable';
    // Blurring or replacing an IME target can discard an uncommitted candidate.
    if (field === composingTarget) return 'composing';
    if (doc.activeElement === field) field.blur();
    return 'ready';
  };
  const onVisibilityChange = () => {
    if (doc.visibilityState === 'hidden') release();
  };
  const onPageHide = () => { release(); };

  doc.addEventListener('compositionstart', onCompositionStart, true);
  doc.addEventListener('compositionend', onCompositionEnd, true);
  doc.addEventListener('visibilitychange', onVisibilityChange);
  win.addEventListener('pagehide', onPageHide);

  return {
    release,
    dispose() {
      doc.removeEventListener('compositionstart', onCompositionStart, true);
      doc.removeEventListener('compositionend', onCompositionEnd, true);
      doc.removeEventListener('visibilitychange', onVisibilityChange);
      win.removeEventListener('pagehide', onPageHide);
      composingTarget = null;
    },
  };
}
