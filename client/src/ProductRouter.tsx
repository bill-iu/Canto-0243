import App from './App.tsx';
import { pageFromPath } from './app-page.ts';
import { WorkbenchPage } from './workbench/WorkbenchPage.tsx';

export function ProductRouter() {
  return pageFromPath(window.location.pathname) === 'workbench' ? <WorkbenchPage /> : <App />;
}
