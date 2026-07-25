import { getAboutCopy } from '../../shared/about-i18n.mjs';

export interface AboutViewProps {
  lang: 'zh' | 'zh-Hans' | 'en';
  lexiconVersion: string;
  onBack: () => void;
}

const ISSUES_URL = 'https://github.com/bill-iu/Canto-0243/issues/new';

function AboutSlogan({ text }: { text: string }) {
  const [line1, line2] = text.split('\n');
  return (
    <>
      {line1}
      <br />
      {line2}
    </>
  );
}

function HtmlBlock({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

export function AboutView({ lang, lexiconVersion, onBack }: AboutViewProps) {
  const c = getAboutCopy(lang);

  return (
    <div className="guide-view about-view">
      <p className="about-slogan about-slogan--top">
        <AboutSlogan text={c.sloganTop} />
      </p>

      <header className="guide-hero">
        <p className="eyebrow">{c.eyebrow}</p>
        <h1 id="aboutTitle" tabIndex={-1}>
          {c.title}
        </h1>
        <p className="about-lede">{c.lede}</p>
        <p className="about-meta">
          {c.lexiconPrefix}{lexiconVersion}
        </p>
        <div className="guide-actions">
          <button type="button" className="primary-button" onClick={onBack}>
            {c.backBtn}
          </button>
        </div>
      </header>

      <article className="guide-card about-block">
        <h2>{c.introTitle}</h2>
        <p>
          <HtmlBlock html={c.introBody} />
        </p>
        <h2>{c.whyTitle}</h2>
        <ul className="about-list" dangerouslySetInnerHTML={{ __html: c.whyList }} />
      </article>

      <article className="guide-card about-block">
        <h2>{c.pledgeTitle}</h2>
        <p>
          <HtmlBlock html={c.pledgeBody1} />
        </p>
        <p>
          <HtmlBlock html={c.pledgeBody2} />
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>{c.thanksTitle}</h2>
        <p>
          <HtmlBlock html={c.thanksBody1} />
        </p>
        <p>
          <HtmlBlock html={c.thanksBody2} />
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>{c.sourcesTitle}</h2>
        <p>{c.sourcesIntro}</p>
        <ul className="about-sources" dangerouslySetInnerHTML={{ __html: c.sourcesList }} />
        <p>
          <HtmlBlock html={c.sourcesFooter} />
        </p>
      </article>

      <article className="guide-card about-block">
        <h2>{c.devTitle}</h2>
        <p>
          <HtmlBlock html={c.devBody} />
        </p>
      </article>

      <article className="guide-card about-block about-report">
        <h2>{c.reportTitle}</h2>
        <p>
          <HtmlBlock html={c.reportBody} />
        </p>
        <div className="about-actions guide-actions">
          <a className="primary-button about-report-btn" href={ISSUES_URL} target="_blank" rel="noopener noreferrer">
            {c.reportBtn}
          </a>
          <button type="button" className="ghost-button" onClick={onBack}>
            {c.backBtn}
          </button>
        </div>
      </article>

      <p className="about-slogan about-slogan--bottom">
        <AboutSlogan text={c.sloganBottom} />
      </p>
    </div>
  );
}
