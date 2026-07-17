export type AppPage = 'search' | 'workbench';

export function pageFromPath(pathname: string, base = import.meta.env.BASE_URL): AppPage {
  const normalizedBase = `/${base.replace(/^\/+|\/+$/g, '')}`.replace(/^\/$/, '');
  const relative = pathname.startsWith(normalizedBase)
    ? pathname.slice(normalizedBase.length)
    : pathname;
  return /^\/workbench(?:\/|$)/.test(relative) ? 'workbench' : 'search';
}

export function searchPageHref(base = import.meta.env.BASE_URL): string {
  return base.endsWith('/') ? base : `${base}/`;
}

export function workbenchPageHref(base = import.meta.env.BASE_URL): string {
  return `${searchPageHref(base)}workbench/`;
}
