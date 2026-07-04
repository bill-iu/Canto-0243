export interface AboutViewProps {
  lexiconVersion: string;
  onBack: () => void;
}

const LICENSE_URL = 'https://github.com/bill-iu/Canto-0243/blob/dev/LICENSE';
const ISSUES_URL = 'https://github.com/bill-iu/Canto-0243/issues/new';
const NOTICES_URL = 'https://github.com/bill-iu/Canto-0243/blob/dev/THIRD_PARTY_NOTICES.md';

export function AboutView({ lexiconVersion, onBack }: AboutViewProps) {
  return (
    <div className="guide-view about-view">
      <p className="about-slogan about-slogan--top">
        即使離線，
        <br />
        亦完全可用。
      </p>

      <header className="guide-hero">
        <p className="eyebrow">About</p>
        <h1 id="aboutTitle" tabIndex={-1}>
          關於 Canto-0243
        </h1>
        <p className="about-lede">{/* bilingual via parent if needed; static for now */}ONE-RUN-RHYME — Offline Cantonese lyric rhyme workbench. / ONE·搵·韻 — 離線粵語填詞查找工作台。</p>
        <p className="about-meta">詞庫版本：{lexiconVersion}</p>
        <div className="guide-actions">
          <button type="button" className="primary-button" onClick={onBack}>
            返回搜尋
          </button>
        </div>
      </header>

      <article className="guide-card about-block">
        <h2>簡介</h2>
        <p>
          填粵語歌詞時，往往要在<strong>同音、押韻、近義</strong>之間快速換字，又要對準 0243
          與粵拼讀音。Canto-0243 用 <strong>0243／02493 數字碼</strong>、<strong>粵拼</strong>、
          <strong>韻母／聲母規則</strong>與<strong>近義／反義關係</strong>
          ，在幾秒內列出符合條件的詞條；套件解壓即用，詞庫與近反義資料存於本地，無需連網。
        </p>
        <h2>為何選擇本工具</h2>
        <ul className="about-list">
          <li>
            <strong>開源</strong> — 原始碼公開，歡迎檢視、改進與回饋
          </li>
          <li>
            <strong>免費</strong> — 下載即用，無訂閱或按量收費
          </li>
          <li>
            <strong>持續更新</strong> — 維護者持續改進詞庫與功能，並透過 Release 發佈
          </li>
        </ul>
      </article>

      <article className="guide-card about-block">
        <h2>承諾與授權</h2>
        <p>
          <strong>本工具 100% 免費、開源。我們絕不會利用本工具或其底層數據牟利。</strong>
          任何創作者皆可將本工具用於<strong>商業創作</strong>
          （例如歌曲、劇本、已發表歌詞），前提為遵守下方限制與{' '}
          <a href={LICENSE_URL} target="_blank" rel="noopener noreferrer">
            Canto-0243 License
          </a>
          （CC BY-NC-SA 4.0 + 附加條款）。
        </p>
        <p>
          <strong>禁止事項（摘要）：</strong>
          不得將本工具重新打包轉售或作為競爭性產品單獨發布；不得提供付費 API、訂閱或按量計費的查詢服務；公開
          fork 或衍生版本須沿用同一授權並保留 Canto-0243 名稱與適當署名。完整條文見 License 連結。
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>專案致謝</h2>
        <p>
          本專案在作者幾乎零程式背景的起步階段，得益於{' '}
          <a href="https://github.com/ivorhoulker" target="_blank" rel="noopener noreferrer">
            ivorhoulker（艾浩家）
          </a>{' '}
          擔任 Advisor，在設計與實行上給予許多指導與寶貴建議。
        </p>
        <p>
          亦要多謝 <strong>「0243 理論」發明人黃志華老師</strong>
          （很榮幸得到他的支持），奠定粵語填詞數碼化的理論基礎。多謝{' '}
          <a href="https://0243.hk" target="_blank" rel="noopener noreferrer">
            0243.hk
          </a>{' '}
          開發者 <strong>Daniel Tam</strong>{' '}
          先生開發該網站，解決許多填詞難題，並啟發本工具的開發。
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>資料來源</h2>
        <p>
          本應用程式得以實現，全賴語言學家、開源維護者及社群貢獻者的出色工作。我們十分榮幸能整合以下項目的數據：
        </p>
        <ul className="about-sources">
          <li>
            <a href="https://words.hk/" target="_blank" rel="noopener noreferrer">
              words.hk（粵典）
            </a>
            ：採用公有領域授權（致謝 words.hk）。
          </li>
          <li>
            <a
              href="https://github.com/CanCLID/rime-cantonese-upstream"
              target="_blank"
              rel="noopener noreferrer"
            >
              Rime 粵語（中州韻粵語拼音）
            </a>
            ：單字讀音與 essay 詞頻；採用{' '}
            <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">
              CC BY 4.0
            </a>
            。
          </li>
          <li>
            <a href="https://kaifangcidian.com/xiazai/" target="_blank" rel="noopener noreferrer">
              開放詞典 · 粵語詞典（Kaifangcidian）
            </a>
            ：採用{' '}
            <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="noopener noreferrer">
              CC BY 3.0
            </a>
            。
          </li>
          <li>
            <a
              href="https://github.com/yaleimeng/Final_word_Similarity"
              target="_blank"
              rel="noopener noreferrer"
            >
              詞林同義詞（Cilin）
            </a>
            ：採用{' '}
            <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener noreferrer">
              MIT
            </a>{' '}
            授權。
          </li>
          <li>
            <a
              href="https://github.com/guotong1988/chinese_dictionary"
              target="_blank"
              rel="noopener noreferrer"
            >
              國語辭典近義／反義（guotong）
            </a>
            ：<code>dict_synonym.txt</code>、<code>dict_antonym.txt</code>；採用{' '}
            <a
              href="https://github.com/996icu/996.ICU/blob/master/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
            >
              Anti-996 License
            </a>
            （反義詞主來源）。
          </li>
        </ul>
        <p>
          完整第三方授權清單見{' '}
          <a href={NOTICES_URL} target="_blank" rel="noopener noreferrer">
            THIRD_PARTY_NOTICES.md
          </a>
          。
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>關於開發者</h2>
        <p>
          <strong>
            <a href="https://github.com/bill-iu/Canto-0243" target="_blank" rel="noopener noreferrer">
              Bill IU（姚程馭）
            </a>
          </strong>{' '}
          — 演員，粵語音樂劇填詞人，超級業餘的程式設計師。
        </p>
      </article>

      <article className="guide-card about-block about-report">
        <h2>錯誤回報</h2>
        <p>
          如果您發現任何問題，請前往 GitHub{' '}
          <a href={ISSUES_URL} target="_blank" rel="noopener noreferrer">
            提交 Issue
          </a>
          （建議使用錯誤回報範本）。非常感謝您的協助！
        </p>
        <div className="about-actions guide-actions">
          <a className="primary-button about-report-btn" href={ISSUES_URL} target="_blank" rel="noopener noreferrer">
            前往 GitHub 回報
          </a>
          <button type="button" className="ghost-button" onClick={onBack}>
            回到搜尋
          </button>
        </div>
      </article>

      <p className="about-slogan about-slogan--bottom">
        呢一次，
        <br />
        拎返你嘅創作主導權。
      </p>
    </div>
  );
}
