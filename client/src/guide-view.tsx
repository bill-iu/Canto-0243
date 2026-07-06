import { getGuideHero, getGuideIntro } from '../../frontend/guide-i18n.mjs';
import { getGuideSections, type GuideExample, type GuideLang, type GuideMode } from './guide-examples';

export interface GuideViewProps {
  lang: GuideLang;
  onPick: (query: string, mode: GuideMode) => void;
}

function HtmlBlock({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

export function GuideView({ lang, onPick }: GuideViewProps) {
  const hero = getGuideHero(lang);
  const intro = getGuideIntro(lang);
  const sections = getGuideSections(lang);

  return (
    <div className="guide-view">
      <header className="guide-hero">
        <p className="eyebrow">{hero.eyebrow}</p>
        <h1 id="guideTitle" tabIndex={-1}>
          {hero.title}
        </h1>
        <p>
          <HtmlBlock html={hero.lede} />
        </p>
      </header>

      <article className="guide-intro" aria-labelledby="guideIntroTitle">
        <h2 id="guideIntroTitle">{intro.title}</h2>
        {intro.paragraphs.map((paragraph) => (
          <p key={paragraph.slice(0, 40)}>
            <HtmlBlock html={paragraph} />
          </p>
        ))}
      </article>

      <div className="guide-grid">
        {sections.map((section) => (
          <article key={section.id} className="guide-card">
            <h3>{section.title}</h3>
            <p>
              <HtmlBlock html={section.intro} />
            </p>
            <div className="guide-examples">
              {section.examples.map((example) => (
                <GuideExampleButton
                  key={`${section.id}-${example.query}-${example.mode}`}
                  example={example}
                  onPick={onPick}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function GuideExampleButton({
  example,
  onPick,
}: {
  example: GuideExample;
  onPick: (query: string, mode: GuideMode) => void;
}) {
  return (
    <button
      type="button"
      className="guide-example"
      title={example.title}
      onClick={() => onPick(example.query, example.mode)}
    >
      <code translate="no">{example.query}</code>
      <span>{example.label}</span>
    </button>
  );
}