import { useEffect, useRef, useState } from 'react';
import {
  bindGuideNav,
  getGuideHero,
  getGuideIntro,
  getGuideGroupLabel,
  getGuideTocCopy,
  getGuidePaneTabs,
  getRhymeGuideCopy,
  guideSectionDomId,
  normalizeGuidePane,
} from '../../shared/guide-i18n.mjs';
import {
  RHYME_PROFILE_LABELS,
  formatFinalWithExample,
  rhymeClassesForProfile,
  rhymeProfileGuideOrder,
  type RhymeProfile,
} from './db/rhyme-match-profile.ts';
import { getGuideSections, type GuideExample, type GuideLang, type GuideMode } from './guide-examples';

export type GuidePane = 'syntax' | 'rhyme';

export interface GuideViewProps {
  lang: GuideLang;
  onPick: (query: string, mode: GuideMode) => void;
  /** URL / parent controlled pane; default syntax */
  pane?: GuidePane;
  onPaneChange?: (pane: GuidePane) => void;
}

function HtmlBlock({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function plainTitle(html: string) {
  return html.replace(/<[^>]+>/g, '');
}

function readPaneFromUrl(): GuidePane {
  if (typeof window === 'undefined') return 'syntax';
  const g = new URLSearchParams(window.location.search).get('guide');
  return normalizeGuidePane(g) as GuidePane;
}

function writePaneToUrl(pane: GuidePane): void {
  if (typeof window === 'undefined') return;
  const params = new URLSearchParams(window.location.search);
  params.set('view', 'guide');
  if (pane === 'syntax') params.delete('guide');
  else params.set('guide', pane);
  const qs = params.toString();
  const next = `${window.location.pathname}${qs ? `?${qs}` : ''}${window.location.hash}`;
  window.history.replaceState(window.history.state, '', next);
}

export function GuideView({ lang, onPick, pane: paneProp, onPaneChange }: GuideViewProps) {
  const rootRef = useRef<HTMLElement>(null);
  const [paneState, setPaneState] = useState<GuidePane>(() => paneProp ?? readPaneFromUrl());
  const pane = paneProp ?? paneState;

  const setPane = (next: GuidePane) => {
    if (!paneProp) setPaneState(next);
    onPaneChange?.(next);
    writePaneToUrl(next);
  };

  useEffect(() => {
    if (paneProp) setPaneState(paneProp);
  }, [paneProp]);

  const tabs = getGuidePaneTabs(lang);
  const hero = getGuideHero(lang);
  const intro = getGuideIntro(lang);
  const sections = getGuideSections(lang);
  const toc = getGuideTocCopy(lang);
  const rhyme = getRhymeGuideCopy(lang);

  const blocks: Array<
    { type: 'group'; label: string } | { type: 'chapter'; section: (typeof sections)[0] }
  > = [];
  if (pane === 'syntax') {
    let lastGroup: string | null = null;
    for (const section of sections) {
      const group = section.group ?? 'advanced';
      if (group !== lastGroup) {
        blocks.push({ type: 'group', label: getGuideGroupLabel(group, lang) });
        lastGroup = group;
      }
      blocks.push({ type: 'chapter', section });
    }
  }

  useEffect(() => {
    if (pane !== 'syntax') return;
    return bindGuideNav(rootRef.current);
  }, [lang, sections.length, pane]);

  return (
    <section className="guide-view" ref={rootRef} aria-labelledby="guideTitle">
      <header className="guide-hero">
        <p className="eyebrow">{hero.eyebrow}</p>
        <h1 id="guideTitle" tabIndex={-1}>
          {pane === 'rhyme' ? rhyme.heroTitle : hero.title}
        </h1>
        <p>
          <HtmlBlock html={pane === 'rhyme' ? rhyme.heroLede : hero.lede} />
        </p>
        <div className="guide-pane-tabs" role="tablist" aria-label="教學子頁">
          <button
            type="button"
            role="tab"
            className={`guide-pane-tab${pane === 'syntax' ? ' is-active' : ''}`}
            aria-selected={pane === 'syntax'}
            onClick={() => setPane('syntax')}
          >
            {tabs.syntax}
          </button>
          <button
            type="button"
            role="tab"
            className={`guide-pane-tab${pane === 'rhyme' ? ' is-active' : ''}`}
            aria-selected={pane === 'rhyme'}
            onClick={() => setPane('rhyme')}
          >
            {tabs.rhyme}
          </button>
        </div>
      </header>

      {pane === 'syntax' ? (
        <>
          <article className="guide-intro" aria-labelledby="guideIntroTitle">
            <h2 id="guideIntroTitle">{intro.title}</h2>
            {intro.paragraphs.map((paragraph: string) => (
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
        </>
      ) : (
        <RhymeGuidePane lang={lang} copy={rhyme} onPick={onPick} />
      )}
    </section>
  );
}

function RhymeGuidePane({
  lang,
  copy,
  onPick,
}: {
  lang: GuideLang;
  copy: ReturnType<typeof getRhymeGuideCopy>;
  onPick: (query: string, mode: GuideMode) => void;
}) {
  const order = rhymeProfileGuideOrder();
  return (
    <div className="guide-rhyme">
      <article className="guide-intro" aria-labelledby="rhymeIntroTitle">
        <h2 id="rhymeIntroTitle">{copy.introTitle}</h2>
        {copy.introParagraphs.map((paragraph: string) => (
          <p key={paragraph.slice(0, 40)}>
            <HtmlBlock html={paragraph} />
          </p>
        ))}
      </article>

      {order.map((profile) => {
        const section = copy.profiles[profile as keyof typeof copy.profiles];
        if (!section) return null;
        const classes = rhymeClassesForProfile(profile);
        return (
          <section
            key={profile}
            className="guide-chapter guide-rhyme-profile"
            id={guideSectionDomId(`rhyme-${profile}`)}
          >
            <h3>
              {section.title}
              <span className="guide-rhyme-profile__badge">
                {RHYME_PROFILE_LABELS[profile as RhymeProfile]}
              </span>
            </h3>
            <p>{section.blurb}</p>
            <p>
              <strong>{lang === 'en' ? 'When: ' : '場合：'}</strong>
              {section.when}
            </p>
            <p>{section.how}</p>
            <div className="guide-examples">
              {section.examples.map((example: { query: string; mode: string; label: string }) => (
                <GuideExampleButton
                  key={`${profile}-${example.query}`}
                  example={{
                    query: example.query,
                    mode: example.mode as GuideMode,
                    label: example.label,
                  }}
                  onPick={onPick}
                />
              ))}
            </div>
            <h4 className="guide-rhyme-groups-title">{copy.groupsHeading}</h4>
            {profile === 'exact' ? (
              <div className="guide-rhyme-exact-grid" aria-label={section.title}>
                {classes.map((cls) => {
                  const final = cls.finals[0]!;
                  return (
                    <code key={final} className="guide-rhyme-chip guide-rhyme-chip--wide" translate="no">
                      {formatFinalWithExample(final)}
                    </code>
                  );
                })}
              </div>
            ) : (
              <div className="guide-rhyme-groups" aria-label={section.title}>
                {classes.map((cls) => (
                  <div key={`${profile}-${cls.name}`} className="guide-rhyme-group">
                    {profile === 'tong' ? (
                      <p className="guide-rhyme-group__name">{cls.name}</p>
                    ) : null}
                    <div className="guide-rhyme-group__grid">
                      {cls.finals.map((final) => (
                        <code key={final} className="guide-rhyme-chip guide-rhyme-chip--wide" translate="no">
                          {formatFinalWithExample(final)}
                        </code>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

function toGuideMode(mode: string): GuideMode {
  if (mode === 'm2' || mode === '02493') return '02493';
  if (mode === 'm3' || mode === '394052') return '394052';
  if (mode === 'syn' || mode === 'synonym') return 'synonym';
  if (mode === 'pz' || mode === 'pingze') return 'pingze';
  return '0243';
}

function GuideExampleButton({
  example,
  onPick,
}: {
  example: GuideExample | { query: string; mode: string; label: string; title?: string };
  onPick: (query: string, mode: GuideMode) => void;
}) {
  const label = example.label;
  const title = 'title' in example && example.title ? example.title : label;
  return (
    <div className="guide-example">
      <button
        type="button"
        className="guide-example__query"
        title={title}
        aria-label={label ? `${example.query}：${label}` : example.query}
        onClick={() => onPick(example.query, toGuideMode(example.mode))}
      >
        <code translate="no">{example.query}</code>
      </button>
      {label ? <span className="guide-example__label">{label}</span> : null}
    </div>
  );
}
