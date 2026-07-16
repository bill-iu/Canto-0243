import { registerSW } from 'virtual:pwa-register';
import { scheduleLexiconPrecache } from './lexicon-precache.ts';

registerSW({
  immediate: true,
  onRegisteredSW() {
    void scheduleLexiconPrecache();
  },
});
