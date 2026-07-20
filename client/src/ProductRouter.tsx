import { useEffect, useState } from 'react';

import App from './App.tsx';
import { pageFromPath } from './app-page.ts';
import { WorkbenchPage } from './workbench/WorkbenchPage.tsx';

export function ProductRouter() {
  const [route, setRoute] = useState(() =>
    typeof window === 'undefined' ? 'search' : pageFromPath(window.location.pathname),
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onPop = () => setRoute(pageFromPath(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  return route === 'workbench' ? <WorkbenchPage /> : <App />;
}
