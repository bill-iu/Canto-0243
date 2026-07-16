import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import '../../frontend/open-design.css';
import '../../frontend/ready-gate.css';
import '../../frontend/shell.css';
import '../../frontend/workbench.css';
import '../../frontend/entry-detail.css';
import './root.css';
import './pwa-app.css';

import App from './App.tsx';
import { BenchmarkApp } from './BenchmarkApp.tsx';
import { DBProvider } from './hooks/db-provider.tsx';
import { isPortableHost } from './host-mode.ts';
import { applyBootThemeFromStorage, hasPwaGateLanded, revealPwaShell } from './pwa-shell-boot';

applyBootThemeFromStorage();
if (hasPwaGateLanded()) {
  revealPwaShell();
}

if (!isPortableHost()) {
  void import('./pwa-register.ts');
}

const benchmark = new URLSearchParams(location.search).has('benchmark');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DBProvider>
      {benchmark ? <BenchmarkApp /> : <App />}
    </DBProvider>
  </StrictMode>,
);
