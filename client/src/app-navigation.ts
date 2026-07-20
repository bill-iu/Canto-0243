import { searchPageHref, workbenchPageHref } from './app-page.ts';

export type AppRoute = 'search' | 'workbench';

function routeToHref(route: AppRoute): string {
  return route === 'workbench' ? workbenchPageHref() : searchPageHref();
}

/**
 * SPA navigation: keep the same DBProvider instance, avoid full page reload,
 * but still update the URL for back/forward + shareability.
 *
 * We dispatch `popstate` because most of our page switching listens to it.
 */
export function navigateAppRoute(route: AppRoute, opts?: { replace?: boolean }): void {
  const href = routeToHref(route);
  try {
    if (opts?.replace) {
      window.history.replaceState({}, '', href);
    } else {
      window.history.pushState({}, '', href);
    }
    window.dispatchEvent(new PopStateEvent('popstate'));
  } catch {
    window.location.href = href;
  }
}

