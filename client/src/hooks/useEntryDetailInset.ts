import { useLayoutEffect } from 'react';

/** Keeps --entry-detail-inset-top aligned with .app-header bottom (ADR-0030 overlay). */
export function useEntryDetailInset(active: boolean): void {
  useLayoutEffect(() => {
    if (!active) return;
    const root = document.documentElement;
    const header = document.querySelector<HTMLElement>('.app-header');
    if (!header) return;

    const sync = () => {
      root.style.setProperty('--entry-detail-inset-top', `${header.getBoundingClientRect().bottom}px`);
    };

    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(header);
    window.addEventListener('resize', sync);
    window.addEventListener('scroll', sync, { passive: true });

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', sync);
      window.removeEventListener('scroll', sync);
      root.style.removeProperty('--entry-detail-inset-top');
    };
  }, [active]);
}