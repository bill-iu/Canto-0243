/** ponytail: P4 mode-meta + search-url self-check */
import { modeMetaSelfCheck } from '../src/mode-meta.ts';
import { searchUrlSelfCheck } from '../src/search-url.ts';

modeMetaSelfCheck();
searchUrlSelfCheck();
console.log('pwa-p4-search-shell-self-check: ok');
