/**
 * ponytail: guide layout contract — TOC + chapters markup.
 * Run: node client/scripts/guide-layout-self-check.mjs
 */
import {
  bindGuideNav,
  guideSectionDomId,
  renderGuideLayoutHtml,
} from '../../frontend/guide-i18n.mjs';

const html = renderGuideLayoutHtml('zh');
const checks = [
  ['has toc', html.includes('class="guide-toc"')],
  ['has chapters wrap', html.includes('class="guide-chapters"')],
  ['has chapter id', html.includes(`id="${guideSectionDomId('basic')}"`)],
  ['no guide-card in layout', !html.includes('guide-card')],
  ['has example row', html.includes('class="guide-example"')],
  ['bindGuideNav noop', typeof bindGuideNav(null) === 'function'],
];

const failed = checks.filter(([, ok]) => !ok);
if (failed.length) {
  console.error('guide-layout-self-check FAIL:', failed.map(([n]) => n).join(', '));
  process.exit(1);
}
console.log('guide-layout-self-check ok');
