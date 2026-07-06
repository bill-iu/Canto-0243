const LICENSE_URL = 'https://github.com/bill-iu/Canto-0243/blob/dev/LICENSE';
const ISSUES_URL = 'https://github.com/bill-iu/Canto-0243/issues/new';
const NOTICES_URL = 'https://github.com/bill-iu/Canto-0243/blob/dev/THIRD_PARTY_NOTICES.md';

/** @type {Record<'zh' | 'en', Record<string, string>>} */
export const ABOUT_COPY = {
  zh: {
    sloganTop: '即使離線，\n亦完全可用。',
    eyebrow: 'About',
    title: '關於 Canto-0243',
    lede: 'ONE·搵·韻 — 離線粵語填詞查找工作台。',
    introTitle: '簡介',
    introBody:
      '填粵語歌詞時，往往要在<strong>同音、押韻、近義</strong>之間快速換字，又要對準 0243 與粵拼讀音。Canto-0243 用 <strong>0243／02493 數字碼</strong>、<strong>粵拼</strong>、<strong>韻母／聲母規則</strong>與<strong>近義／反義關係</strong>，在幾秒內列出符合條件的詞條；套件解壓即用，詞庫與近反義資料存於本地，無需連網。',
    whyTitle: '為何選擇本工具',
    whyList:
      '<li><strong>開源</strong> — 原始碼公開，歡迎檢視、改進與回饋</li>' +
      '<li><strong>免費</strong> — 下載即用，無訂閱或按量收費</li>' +
      '<li><strong>持續更新</strong> — 維護者持續改進詞庫與功能，並透過 Release 發佈</li>',
    pledgeTitle: '承諾與授權',
    pledgeBody1:
      '<strong>本工具 100% 免費、開源。我們絕不會利用本工具或其底層數據牟利。</strong>任何創作者皆可將本工具用於<strong>商業創作</strong>（例如歌曲、劇本、已發表歌詞），前提為遵守下方限制與 <a href="' +
      LICENSE_URL +
      '" target="_blank" rel="noopener noreferrer">Canto-0243 License</a>（CC BY-NC-SA 4.0 + 附加條款）。',
    pledgeBody2:
      '<strong>禁止事項（摘要）：</strong>不得將本工具重新打包轉售或作為競爭性產品單獨發布；不得提供付費 API、訂閱或按量計費的查詢服務；公開 fork 或衍生版本須沿用同一授權並保留 Canto-0243 名稱與適當署名。完整條文見 License 連結。',
    thanksTitle: '專案致謝',
    thanksBody1:
      '本專案在作者幾乎零程式背景的起步階段，得益於 <a href="https://github.com/ivorhoulker" target="_blank" rel="noopener noreferrer">ivorhoulker（艾浩家）</a> 擔任 Advisor，在設計與實行上給予許多指導與寶貴建議。',
    thanksBody2:
      '亦要多謝 <strong>「0243 理論」發明人黃志華老師</strong>（很榮幸得到他的支持），奠定粵語填詞數碼化的理論基礎。多謝 <a href="https://0243.hk" target="_blank" rel="noopener noreferrer">0243.hk</a> 開發者 <strong>Daniel Tam</strong> 先生開發該網站，解決許多填詞難題，並啟發本工具的開發。',
    sourcesTitle: '資料來源',
    sourcesIntro:
      '本應用程式得以實現，全賴語言學家、開源維護者及社群貢獻者的出色工作。我們十分榮幸能整合以下項目的數據：',
    sourcesList:
      '<li><a href="https://words.hk/" target="_blank" rel="noopener noreferrer">words.hk（粵典）</a>：採用<strong>非商業開放授權</strong>（詳見 <a href="https://words.hk/base/hoifong/" target="_blank" rel="noopener noreferrer">words.hk /hoifong</a>）。</li>' +
      '<li><a href="https://github.com/CanCLID/rime-cantonese-upstream" target="_blank" rel="noopener noreferrer">Rime 粵語詞典補缺來源</a>：採用 <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>。</li>' +
      '<li><a href="https://github.com/elkmovie/hsk30" target="_blank" rel="noopener noreferrer">HSK 3.0 詞表</a>：採用 <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">MIT</a> 授權。</li>' +
      '<li><a href="https://kaifangcidian.com/xiazai/" target="_blank" rel="noopener noreferrer">開放詞典 · 粵語詞典（Kaifangcidian）</a>：採用 <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="noopener noreferrer">CC BY 3.0</a>。</li>' +
      '<li><a href="https://github.com/yaleimeng/Final_word_Similarity" target="_blank" rel="noopener noreferrer">詞林同義詞（Cilin）</a>：採用 <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">MIT</a> 授權。</li>' +
      '<li><a href="https://github.com/guotong1988/chinese_dictionary" target="_blank" rel="noopener noreferrer">國語辭典近義／反義（guotong）</a>：<code>dict_synonym.txt</code>、<code>dict_antonym.txt</code>；採用 <a href="https://github.com/996icu/996.ICU/blob/master/LICENSE" target="_blank" rel="noopener noreferrer">Anti-996 License</a>（反義詞主來源）。</li>',
    sourcesFooter:
      '完整第三方授權清單見 <a href="' +
      NOTICES_URL +
      '" target="_blank" rel="noopener noreferrer">THIRD_PARTY_NOTICES.md</a>。',
    devTitle: '關於開發者',
    devBody:
      '<strong><a href="https://github.com/bill-iu/Canto-0243" target="_blank" rel="noopener noreferrer">Bill IU（姚程馭）</a></strong> — 演員，粵語音樂劇填詞人，超級業餘的程式設計師。',
    reportTitle: '錯誤回報',
    reportBody:
      '如果您發現任何問題，請前往 GitHub <a href="' +
      ISSUES_URL +
      '" target="_blank" rel="noopener noreferrer">提交 Issue</a>（建議使用錯誤回報範本）。非常感謝您的協助！',
    reportBtn: '前往 GitHub 回報',
    backBtn: '回到搜尋',
    sloganBottom: '這一次，\n重奪你的創作主導權。',
  },
  en: {
    sloganTop: 'Fully usable—\neven offline.',
    eyebrow: 'About',
    title: 'About Canto-0243',
    lede: 'ONE-RUN-RHYME — Offline Cantonese lyric lookup workbench.',
    introTitle: 'Introduction',
    introBody:
      'When writing Cantonese lyrics, you often need to swap characters quickly among <strong>same-tone, rhyming, and near-synonym</strong> options while matching 0243 codes and Jyutping. Canto-0243 uses <strong>0243／02493 tone codes</strong>, <strong>Jyutping</strong>, <strong>rhyme／initial rules</strong>, and <strong>synonym／antonym relations</strong> to list matching word entries in seconds. Unzip and run—lexicon and relation data stay on your device, no internet required.',
    whyTitle: 'Why choose this tool',
    whyList:
      '<li><strong>Open source</strong> — source code is public; review, improve, and feedback welcome</li>' +
      '<li><strong>Free</strong> — download and use; no subscription or pay-per-use fees</li>' +
      '<li><strong>Actively maintained</strong> — lexicon and features keep improving via Releases</li>',
    pledgeTitle: 'Commitment & license',
    pledgeBody1:
      '<strong>This tool is 100% free and open source. We will never profit from this tool or its underlying data.</strong> Any creator may use it for <strong>commercial creative work</strong> (songs, scripts, published lyrics) provided you follow the restrictions below and the <a href="' +
      LICENSE_URL +
      '" target="_blank" rel="noopener noreferrer">Canto-0243 License</a> (CC BY-NC-SA 4.0 + additional terms).',
    pledgeBody2:
      '<strong>Restrictions (summary):</strong> You may not repackage and resell this tool or ship it as a competing standalone product; you may not offer a paid API, subscription, or metered query service; public forks and derivatives must use the same license and keep the Canto-0243 name with proper attribution. See the License link for full terms.',
    thanksTitle: 'Project thanks',
    thanksBody1:
      'Early in development—with almost no programming background—the author benefited from <a href="https://github.com/ivorhoulker" target="_blank" rel="noopener noreferrer">ivorhoulker</a> as advisor, with design and implementation guidance plus many valuable suggestions.',
    thanksBody2:
      'Thanks also to <strong>Professor Wong Chi-wah</strong>, inventor of <strong>0243 theory</strong> (whose support we are honoured to have), for the theoretical foundation of digitized Cantonese lyric writing; and to <strong>Daniel Tam</strong>, developer of <a href="https://0243.hk" target="_blank" rel="noopener noreferrer">0243.hk</a>, whose site solved many lyricists’ problems and inspired this tool.',
    sourcesTitle: 'Data sources',
    sourcesIntro:
      'This app exists thanks to outstanding work by linguists, open-source maintainers, and community contributors. We are proud to integrate data from:',
    sourcesList:
      '<li><a href="https://words.hk/" target="_blank" rel="noopener noreferrer">words.hk (粵典)</a>: <strong>non-commercial open license</strong> (see <a href="https://words.hk/base/hoifong/" target="_blank" rel="noopener noreferrer">words.hk /hoifong</a>).</li>' +
      '<li><a href="https://github.com/CanCLID/rime-cantonese-upstream" target="_blank" rel="noopener noreferrer">Rime Cantonese supplement sources</a>: <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>.</li>' +
      '<li><a href="https://github.com/elkmovie/hsk30" target="_blank" rel="noopener noreferrer">HSK 3.0 word list</a>: <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">MIT</a>.</li>' +
      '<li><a href="https://kaifangcidian.com/xiazai/" target="_blank" rel="noopener noreferrer">Kaifang Dictionary · Cantonese</a>: <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="noopener noreferrer">CC BY 3.0</a>.</li>' +
      '<li><a href="https://github.com/yaleimeng/Final_word_Similarity" target="_blank" rel="noopener noreferrer">Cilin synonyms</a>: <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">MIT</a>.</li>' +
      '<li><a href="https://github.com/guotong1988/chinese_dictionary" target="_blank" rel="noopener noreferrer">Guotong near／antonym dictionary</a>: <code>dict_synonym.txt</code>, <code>dict_antonym.txt</code>; <a href="https://github.com/996icu/996.ICU/blob/master/LICENSE" target="_blank" rel="noopener noreferrer">Anti-996 License</a> (primary antonym source).</li>',
    sourcesFooter:
      'Full third-party license list: <a href="' +
      NOTICES_URL +
      '" target="_blank" rel="noopener noreferrer">THIRD_PARTY_NOTICES.md</a>.',
    devTitle: 'About the developer',
    devBody:
      '<strong><a href="https://github.com/bill-iu/Canto-0243" target="_blank" rel="noopener noreferrer">Bill IU (姚程馭)</a></strong> — actor, Cantonese musical theatre lyricist, and extremely amateur programmer.',
    reportTitle: 'Report issues',
    reportBody:
      'If you find a problem, please <a href="' +
      ISSUES_URL +
      '" target="_blank" rel="noopener noreferrer">open an Issue on GitHub</a> (the bug-report template is recommended). Thank you for your help!',
    reportBtn: 'Report on GitHub',
    backBtn: 'Back to search',
    sloganBottom: 'This time,\ntake back control of your creative process.',
  },
};

export function getAboutCopy(lang) {
  return ABOUT_COPY[lang === 'en' ? 'en' : 'zh'];
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function setSlogan(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  const [line1, line2] = text.split('\n');
  el.innerHTML = `${line1}<br>${line2 ?? ''}`;
}

/** Apply About page copy for vanilla frontend (#aboutView). */
export function applyAboutLang(lang) {
  const c = getAboutCopy(lang);
  setSlogan('aboutSloganTop', c.sloganTop);
  setText('aboutEyebrow', c.eyebrow);
  setText('aboutTitle', c.title);
  setText('aboutLede', c.lede);
  setText('aboutIntroTitle', c.introTitle);
  setHtml('aboutIntroBody', c.introBody);
  setText('aboutWhyTitle', c.whyTitle);
  setHtml('aboutWhyList', c.whyList);
  setText('aboutPledgeTitle', c.pledgeTitle);
  setHtml('aboutPledgeBody1', c.pledgeBody1);
  setHtml('aboutPledgeBody2', c.pledgeBody2);
  setText('aboutThanksTitle', c.thanksTitle);
  setHtml('aboutThanksBody1', c.thanksBody1);
  setHtml('aboutThanksBody2', c.thanksBody2);
  setText('aboutSourcesTitle', c.sourcesTitle);
  setText('aboutSourcesIntro', c.sourcesIntro);
  setHtml('aboutSourcesList', c.sourcesList);
  setHtml('aboutSourcesFooter', c.sourcesFooter);
  setText('aboutDevTitle', c.devTitle);
  setHtml('aboutDevBody', c.devBody);
  setText('aboutReportTitle', c.reportTitle);
  setHtml('aboutReportBody', c.reportBody);
  const reportBtn = document.getElementById('aboutReportBtn');
  if (reportBtn) reportBtn.textContent = c.reportBtn;
  const backBtn = document.getElementById('aboutBackToSearchBtn');
  if (backBtn) backBtn.textContent = c.backBtn;
  setSlogan('aboutSloganBottom', c.sloganBottom);
}