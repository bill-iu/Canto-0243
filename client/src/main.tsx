import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import '../../shared/open-design.css';
import '../../shared/ready-gate.css';
import '../../shared/shell.css';
import '../../shared/workbench.css';
import '../../shared/entry-detail.css';
import './root.css';
import './pwa-app.css';

import { ProductRouter } from './ProductRouter.tsx';
import { BenchmarkApp } from './BenchmarkApp.tsx';
import { DBProvider } from './hooks/db-provider.tsx';
import { isPortableHost } from './host-mode.ts';
import { installDesktopSessionLifecycle } from './desktop-session.ts';
import { applyBootThemeFromStorage, hasPwaGateLanded, revealPwaShell } from './pwa-shell-boot';
import { getInitializedDbBackendMode } from './db/init.ts';
import { getOpfsVfsWorkerDebugState } from './db/opfs-vfs-backend.ts';
import { installResumeDebug } from './resume-debug.ts';

applyBootThemeFromStorage();
installResumeDebug({
  getBackendMode: getInitializedDbBackendMode,
  getWorkerState: getOpfsVfsWorkerDebugState,
});
if (hasPwaGateLanded()) {
  revealPwaShell();
}

if (isPortableHost()) {
  installDesktopSessionLifecycle();
} else {
  void import('./pwa-register.ts');
}

const benchmark = new URLSearchParams(location.search).has('benchmark');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DBProvider>
      {benchmark ? <BenchmarkApp /> : <ProductRouter />}
    </DBProvider>
  </StrictMode>,
);
