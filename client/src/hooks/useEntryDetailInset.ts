import { useLayoutEffect } from 'react';

/** Keeps --entry-detail-inset-top aligned with .app-header bottom (ADR-0030 overlay). */
export function useEntryDetailInset(active: boolean): void {
  useLayoutEffect(() => {
    if (!active) return;
    const root = document.documentElement;
    const header = document.querySelector<HTMLElement>('.app-header');
    if (!header) return;

    root.classList.add('has-entry-detail-open');

    const sync = () => {
      root.style.setProperty('--entry-detail-inset-top', `${header.getBoundingClientRect().bottom}px`);
    };

    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(header);
    window.addEventListener('resize', sync);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', sync);
      root.classList.remove('has-entry-detail-open');
      root.style.removeProperty('--entry-detail-inset-top');
    };
  }, [active]);
}