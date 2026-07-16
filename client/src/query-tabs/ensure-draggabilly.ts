/** Load vendored Draggabilly onto globalThis (classic UMD; Vite ESM would hit CJS require). */
import draggabillyUrl from '../../../shared/vendor/draggabilly.pkgd.min.js?url';

declare global {
  var Draggabilly:
    | (new (
        element: Element,
        options?: { axis?: string; handle?: string; containment?: Element | string },
      ) => {
        on: (event: string, cb: (...args: unknown[]) => void) => void;
        destroy: () => void;
      })
    | undefined;
}

let loadPromise: Promise<void> | null = null;

export function ensureDraggabilly(): Promise<void> {
  if (typeof globalThis.Draggabilly === 'function') return Promise.resolve();
  if (loadPromise) return loadPromise;
  loadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-canto-draggabilly]');
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Draggabilly load failed')), {
        once: true,
      });
      return;
    }
    const script = document.createElement('script');
    script.src = draggabillyUrl;
    script.async = true;
    script.dataset.cantoDraggabilly = '1';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Draggabilly load failed'));
    document.head.appendChild(script);
  });
  return loadPromise;
}
