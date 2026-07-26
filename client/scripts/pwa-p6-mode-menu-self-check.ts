/** ponytail: P6 mode menu + view URL sync */
import { modeMenuSelfCheck } from '../src/mode-menu-logic.ts';
import { modeMetaSelfCheck } from '../src/mode-meta.ts';
import { searchUrlSelfCheck } from '../src/search-url.ts';
import { modeMenuI18nSelfCheck } from '../../shared/mode-menu-i18n.mjs';

modeMetaSelfCheck();
searchUrlSelfCheck();
modeMenuSelfCheck();
modeMenuI18nSelfCheck();
console.log('pwa-p6-mode-menu-self-check: ok');
