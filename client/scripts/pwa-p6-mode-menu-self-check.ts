/** ponytail: P6 mode menu + view URL sync */
import { modeMenuSelfCheck } from '../src/mode-menu-logic.ts';
import { modeMetaSelfCheck } from '../src/mode-meta.ts';
import { searchUrlSelfCheck } from '../src/search-url.ts';

modeMetaSelfCheck();
searchUrlSelfCheck();
modeMenuSelfCheck();
console.log('pwa-p6-mode-menu-self-check: ok');
