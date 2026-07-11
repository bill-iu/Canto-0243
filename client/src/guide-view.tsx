import { useEffect, useRef } from 'react';
import {
  bindGuideNav,
  getGuideHero,
  getGuideIntro,
  getGuideGroupLabel,
  getGuideTocCopy,
  guideSectionDomId,
} from '../../frontend/guide-i18n.mjs';
import { getGuideSections, type GuideExample, type GuideLang, type GuideMode } from './guide-examples';

export interface GuideViewProps {
  lang: GuideLang;
  onPick: (query: string, mode: GuideMode) => void;
}

function HtmlBlock({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function plainTitle(html: string) {
  return html.replace(/<[^>]+>/g, '');
}

export function GuideView({ lang, onPick }: GuideViewProps) {
  const rootRef = useRef<HTMLElement>(null);
  const hero = getGuideHero(lang);
  const intro = getGuideIntro(lang);
  const sections = getGuideSections(lang);
  const toc = getGuideTocCopy(lang);

  const blocks: Array<
    { type: 'group'; label: string } | { type: 'chapter'; section: (typeof sections)[0] }
  > = [];
  let lastGroup: string | null = null;
  for (const section of sections) {
    const group = section.group ?? 'advanced';
    if (group !== lastGroup) {
      blocks.push({ type: 'group', label: getGuideGroupLabel(group, lang) });
      lastGroup = group;
    }
    blocks.push({ type: 'chapter', section });
  }

  useEffect(() => bindGuideNav(rootRef.current), [lang, sections.length]);

  return (
    <section className="guide-view" ref={rootRef} aria-labelledby="guideTitle">
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

      <div className="guide-layout">
        <nav className="guide-toc" aria-label={toc.label}>
          <button
            type="button"
            className="guide-toc__toggle"
            aria-expanded="false"
            aria-controls="guideTocPanel"
          >
            {toc.label}
          </button>
          <div className="guide-toc__panel" id="guideTocPanel">
            <p className="guide-toc__title">{toc.label}</p>
            <ol className="guide-toc__list">
              {sections.map((section) => (
                <li key={section.id}>
                  <a className="guide-toc__link" href={`#${guideSectionDomId(section.id)}`}>
                    {plainTitle(section.title)}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        </nav>

        <div className="guide-chapters" id="guideGrid">
          {blocks.map((block) =>
            block.type === 'group' ? (
              <h2 key={`group-${block.label}`} className="guide-group-label">
                {block.label}
              </h2>
            ) : (
              <section
                key={block.section.id}
                className="guide-chapter"
                id={guideSectionDomId(block.section.id)}
              >
                <h3>
                  <HtmlBlock
                    html={block.section.title
                      .replace(/（\+）/g, '（<code translate="no">+</code>）')
                      .replace(/（=）/g, '（<code translate="no">=</code>）')}
                  />
                </h3>
                <p>
                  <HtmlBlock html={block.section.intro} />
                </p>
                <div className="guide-examples">
                  {block.section.examples.map((example) => (
                    <GuideExampleButton
                      key={`${block.section.id}-${example.query}-${example.mode}`}
                      example={example}
                      onPick={onPick}
                    />
                  ))}
                </div>
              </section>
            ),
          )}
        </div>
      </div>
    </section>
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
